"""Minimax regret portfolio optimization solver.

Implements a binary integer linear program that selects initiatives
minimizing worst-case regret across best, median, and worst-case scenarios.
Uses PuLP with the CBC solver.
"""

import logging
import math
from collections.abc import Callable
from typing import Any

import pulp as lp

logger = logging.getLogger(__name__)

SCENARIOS = ["best", "med", "worst"]


def calculate_gamma(confidence_score: float) -> float:
    """Convert a confidence score to a penalty factor.

    Parameters
    ----------
    confidence_score : float
        Confidence in the initiative's estimates, between 0 and 1.

    Returns
    -------
    float
        Penalty factor gamma = 1 - confidence.

    Raises
    ------
    ValueError
        If confidence_score is outside [0, 1].
    """
    if not (0 <= confidence_score <= 1):
        raise ValueError("Confidence score must be between 0 and 1.")
    return 1 - confidence_score


def calculate_effective_returns(
    initiatives: list[dict[str, Any]],
    confidence_penalty_func: Callable[[float], float] = calculate_gamma,
) -> list[dict[str, Any]]:
    """Calculate confidence-penalized effective returns for each initiative.

    Blends each scenario's base return toward the worst-case return,
    weighted by the penalty factor gamma. Does not mutate input.

    Parameters
    ----------
    initiatives : list[dict[str, Any]]
        Each dict must have keys: ``confidence``, ``R_best``, ``R_med``,
        ``R_worst``.
    confidence_penalty_func : Callable[[float], float], optional
        Maps confidence to penalty factor gamma. Default: ``1 - confidence``.

    Returns
    -------
    list[dict[str, Any]]
        New list of dicts, each augmented with ``gamma`` and
        ``effective_returns`` keys.
    """
    result = []
    for initiative in initiatives:
        c_i = initiative["confidence"]
        gamma_i = confidence_penalty_func(c_i)
        r_base_map = {
            "best": initiative["R_best"],
            "med": initiative["R_med"],
            "worst": initiative["R_worst"],
        }
        effective_returns = {}
        for scenario_name in SCENARIOS:
            r_ij_base = r_base_map[scenario_name]
            effective_returns[scenario_name] = (1 - gamma_i) * r_ij_base + gamma_i * initiative["R_worst"]
        result.append({**initiative, "gamma": gamma_i, "effective_returns": effective_returns})
    return result


def calculate_optimal_scenario_returns(
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


def solve_minimax_regret(
    initiatives_data: list[dict[str, Any]],
    total_budget: float,
    min_confidence_threshold: float,
    min_portfolio_worst_return: float,
    confidence_penalty_func: Callable[[float], float] = calculate_gamma,
) -> dict[str, Any]:
    """Solve the minimax regret portfolio selection problem.

    Selects a subset of initiatives that minimizes the maximum regret
    across best, median, and worst-case scenarios, subject to budget
    and minimum worst-case return constraints.

    Parameters
    ----------
    initiatives_data : list[dict[str, Any]]
        Each dict must have keys: ``id``, ``cost``, ``R_best``, ``R_med``,
        ``R_worst``, ``confidence``.
    total_budget : float
        Maximum total cost of selected initiatives.
    min_confidence_threshold : float
        Initiatives below this confidence are excluded.
    min_portfolio_worst_return : float
        Minimum aggregate worst-case return for the portfolio.
    confidence_penalty_func : Callable[[float], float], optional
        Maps confidence to penalty factor gamma. Default: ``1 - confidence``.

    Returns
    -------
    dict[str, Any]
        Result dict with keys: ``status``, ``min_max_regret``,
        ``selected_initiatives``, ``total_cost``, ``total_actual_returns``,
        ``v_j_star``, ``regrets_for_selected_portfolio``.
    """
    empty_result = {
        "status": "",
        "min_max_regret": None,
        "selected_initiatives": [],
        "total_cost": 0,
        "total_actual_returns": {s: 0 for s in SCENARIOS},
        "v_j_star": {},
        "regrets_for_selected_portfolio": {},
    }

    eligible_initiatives = [i for i in initiatives_data if i["confidence"] >= min_confidence_threshold]
    if not eligible_initiatives:
        return {**empty_result, "status": "No Eligible Initiatives"}

    processed_initiatives = calculate_effective_returns(eligible_initiatives, confidence_penalty_func)
    v_j_star = calculate_optimal_scenario_returns(processed_initiatives, total_budget)

    if any(val == -math.inf for val in v_j_star.values()):
        return {**empty_result, "status": "Error in V_j_star calculation", "v_j_star": v_j_star}

    logger.info("Formulating minimax regret problem")
    prob = lp.LpProblem("Minimax_Regret_Investment_Portfolio", lp.LpMinimize)
    x = lp.LpVariable.dicts("Select", [i["id"] for i in processed_initiatives], 0, 1, lp.LpBinary)
    theta = lp.LpVariable("Max_Regret", lowBound=0)
    prob += theta

    for scenario_name in SCENARIOS:
        prob += theta >= v_j_star[scenario_name] - lp.lpSum(
            x[i["id"]] * i["effective_returns"][scenario_name] for i in processed_initiatives
        )

    prob += lp.lpSum(x[i["id"]] * i["cost"] for i in processed_initiatives) <= total_budget
    prob += lp.lpSum(x[i["id"]] * i["R_worst"] for i in processed_initiatives) >= min_portfolio_worst_return

    logger.info("Solving the main optimization problem")
    try:
        prob.solve(lp.PULP_CBC_CMD(msg=False))
    except Exception:
        logger.exception("Error solving main problem")
        return {**empty_result, "status": "Error solving main problem", "v_j_star": v_j_star}

    results: dict[str, Any] = {}
    results["status"] = lp.LpStatus[prob.status]
    results["min_max_regret"] = lp.value(prob.objective) if prob.status == lp.LpStatusOptimal else None

    selected_initiatives: list[str] = []
    total_cost = 0.0
    total_actual_returns = {s: 0.0 for s in SCENARIOS}
    regrets_for_selected_portfolio = {s: 0.0 for s in SCENARIOS}

    if prob.status == lp.LpStatusOptimal:
        for i in processed_initiatives:
            if x[i["id"]].varValue > 0.5:
                selected_initiatives.append(i["id"])
                total_cost += i["cost"]
                for scenario_name in SCENARIOS:
                    total_actual_returns[scenario_name] += i["effective_returns"][scenario_name]

        for scenario_name in SCENARIOS:
            regrets_for_selected_portfolio[scenario_name] = v_j_star[scenario_name] - total_actual_returns[scenario_name]

    results["selected_initiatives"] = selected_initiatives
    results["total_cost"] = total_cost
    results["total_actual_returns"] = total_actual_returns
    results["v_j_star"] = v_j_star
    results["regrets_for_selected_portfolio"] = regrets_for_selected_portfolio

    return results
