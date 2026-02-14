"""Minimax regret decision rule.

Selects a portfolio that minimizes the maximum regret across scenarios.
Regret for a scenario is the difference between the optimal achievable
return (V_j_star) and the portfolio's return under that scenario.
"""

import logging
import math
from typing import Any

import pulp as lp

from portfolio_allocation.solver._common import SCENARIOS, empty_solver_result, extract_selection
from portfolio_allocation.solver._types import SolverResult

logger = logging.getLogger(__name__)


def _calculate_optimal_scenario_returns(
    initiatives: list[dict[str, Any]],
    total_budget: float,
) -> dict[str, float]:
    """Calculate the optimal return achievable under each scenario independently.

    For each scenario, solves a separate binary knapsack problem to find
    the maximum effective return within the budget.

    Parameters
    ----------
    initiatives : list[dict[str, Any]]
        Initiatives with ``effective_returns`` already computed.
    total_budget : float
        Maximum total cost.

    Returns
    -------
    dict[str, float]
        Mapping from scenario name to optimal return ``V_j_star``.
        Returns ``-inf`` for any scenario that fails to solve.
    """
    v_j_star: dict[str, float] = {}
    logger.info("Calculating optimal scenario returns (V_j_star)")
    for scenario_name in SCENARIOS:
        prob_scenario = lp.LpProblem(f"Optimal_Return_Scenario_{scenario_name}", lp.LpMaximize)
        y = lp.LpVariable.dicts("Select", [i["id"] for i in initiatives], 0, 1, lp.LpBinary)
        prob_scenario += lp.lpSum(y[i["id"]] * i["effective_returns"][scenario_name] for i in initiatives)
        prob_scenario += lp.lpSum(y[i["id"]] * i["cost"] for i in initiatives) <= total_budget
        try:
            prob_scenario.solve(lp.PULP_CBC_CMD(msg=False))
        except Exception:
            logger.exception("Error solving for scenario %s", scenario_name)
            v_j_star[scenario_name] = -math.inf
            continue
        if lp.LpStatus[prob_scenario.status] == "Optimal":
            v_j_star[scenario_name] = lp.value(prob_scenario.objective)
            logger.info("Scenario '%s': V_j_star = %.2f", scenario_name, v_j_star[scenario_name])
        else:
            v_j_star[scenario_name] = -math.inf
            logger.warning("Scenario '%s': status = %s", scenario_name, lp.LpStatus[prob_scenario.status])
    return v_j_star


class MinimaxRegretSolver:
    """Minimax regret decision rule.

    Minimizes the maximum regret across best, median, and worst-case
    scenarios, subject to budget and minimum worst-case return constraints.

    This solver receives **preprocessed** initiatives (with
    ``effective_returns`` already computed by the shared preprocessing step).
    """

    def __call__(
        self,
        initiatives: list[dict[str, Any]],
        total_budget: float,
        min_portfolio_worst_return: float,
    ) -> SolverResult:
        """Solve the minimax regret portfolio selection problem.

        Parameters
        ----------
        initiatives : list[dict[str, Any]]
            Preprocessed initiatives with ``effective_returns``.
        total_budget : float
            Maximum total cost of selected initiatives.
        min_portfolio_worst_return : float
            Minimum aggregate worst-case return for the portfolio.

        Returns
        -------
        SolverResult
        """
        scenarios = SCENARIOS

        v_j_star = _calculate_optimal_scenario_returns(initiatives, total_budget)

        if any(val == -math.inf for val in v_j_star.values()):
            result = empty_solver_result("Error in V_j_star calculation", "minimax_regret")
            result["detail"] = {"v_j_star": v_j_star, "regrets": {}}
            return result

        logger.info("Formulating minimax regret problem")
        prob = lp.LpProblem("Minimax_Regret_Investment_Portfolio", lp.LpMinimize)
        x = lp.LpVariable.dicts("Select", [i["id"] for i in initiatives], 0, 1, lp.LpBinary)
        theta = lp.LpVariable("Max_Regret", lowBound=0)
        prob += theta

        for scenario_name in scenarios:
            prob += theta >= v_j_star[scenario_name] - lp.lpSum(
                x[i["id"]] * i["effective_returns"][scenario_name] for i in initiatives
            )

        prob += lp.lpSum(x[i["id"]] * i["cost"] for i in initiatives) <= total_budget
        prob += lp.lpSum(x[i["id"]] * i["R_worst"] for i in initiatives) >= min_portfolio_worst_return

        logger.info("Solving the main optimization problem")
        try:
            prob.solve(lp.PULP_CBC_CMD(msg=False))
        except Exception:
            logger.exception("Error solving minimax regret problem")
            result = empty_solver_result("Error solving main problem", "minimax_regret")
            result["detail"] = {"v_j_star": v_j_star, "regrets": {}}
            return result

        status = lp.LpStatus[prob.status]
        objective_value = lp.value(prob.objective) if prob.status == lp.LpStatusOptimal else None

        if prob.status == lp.LpStatusOptimal:
            selected, total_cost, total_actual_returns = extract_selection(x, initiatives, scenarios)
        else:
            selected, total_cost, total_actual_returns = [], 0.0, {s: 0.0 for s in scenarios}

        regrets = {s: v_j_star[s] - total_actual_returns[s] for s in scenarios}

        return {
            "status": status,
            "selected_initiatives": selected,
            "total_cost": total_cost,
            "objective_value": objective_value,
            "total_actual_returns": total_actual_returns,
            "rule": "minimax_regret",
            "detail": {"v_j_star": v_j_star, "regrets": regrets},
        }
