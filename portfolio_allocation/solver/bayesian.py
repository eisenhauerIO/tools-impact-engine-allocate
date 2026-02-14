"""Bayesian (weighted-scenario) decision rule.

Selects a portfolio that maximizes the expected return under user-specified
scenario probability weights. The Laplace criterion is the special case
where all weights are equal.
"""

import logging
from typing import Any

import pulp as lp

from portfolio_allocation.solver._common import empty_solver_result, extract_selection
from portfolio_allocation.solver._types import SolverResult

logger = logging.getLogger(__name__)


class BayesianSolver:
    """Bayesian expected-return decision rule.

    Maximizes the weighted sum of scenario returns, where weights represent
    the decision-maker's prior beliefs about scenario likelihoods.

    Parameters
    ----------
    weights : dict[str, float]
        Mapping from scenario name to probability weight. Must be
        non-negative and sum to 1. Keys must match the scenario names
        in the preprocessed initiatives' ``effective_returns``.

    Raises
    ------
    ValueError
        If weights are negative or do not sum to 1.
    """

    def __init__(self, weights: dict[str, float]) -> None:
        if any(w < 0 for w in weights.values()):
            raise ValueError("Weights must be non-negative.")
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            raise ValueError("Weights must sum to 1.")
        self.weights = dict(weights)

    def __call__(
        self,
        initiatives: list[dict[str, Any]],
        total_budget: float,
        min_portfolio_worst_return: float,
    ) -> SolverResult:
        """Solve the Bayesian portfolio selection problem.

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
        scenarios = list(self.weights.keys())

        # Per-initiative weighted return (arithmetic — no LP needed).
        weighted_returns: dict[str, float] = {}
        for i in initiatives:
            weighted_returns[i["id"]] = sum(
                self.weights[s] * i["effective_returns"][s] for s in scenarios
            )

        logger.info("Formulating Bayesian expected-return problem")
        prob = lp.LpProblem("Bayesian_Portfolio", lp.LpMaximize)
        x = lp.LpVariable.dicts("Select", [i["id"] for i in initiatives], 0, 1, lp.LpBinary)

        prob += lp.lpSum(x[i["id"]] * weighted_returns[i["id"]] for i in initiatives)
        prob += lp.lpSum(x[i["id"]] * i["cost"] for i in initiatives) <= total_budget
        prob += lp.lpSum(x[i["id"]] * i["R_worst"] for i in initiatives) >= min_portfolio_worst_return

        logger.info("Solving the Bayesian optimization problem")
        try:
            prob.solve(lp.PULP_CBC_CMD(msg=False))
        except Exception:
            logger.exception("Error solving Bayesian problem")
            return empty_solver_result("Error solving main problem", "bayesian", scenarios)

        status = lp.LpStatus[prob.status]
        objective_value = lp.value(prob.objective) if prob.status == lp.LpStatusOptimal else None

        if prob.status == lp.LpStatusOptimal:
            selected, total_cost, total_actual_returns = extract_selection(x, initiatives, scenarios)
        else:
            selected, total_cost, total_actual_returns = [], 0.0, {s: 0.0 for s in scenarios}

        return {
            "status": status,
            "selected_initiatives": selected,
            "total_cost": total_cost,
            "objective_value": objective_value,
            "total_actual_returns": total_actual_returns,
            "rule": "bayesian",
            "detail": {
                "weights": self.weights,
                "weighted_returns": {sid: weighted_returns[sid] for sid in selected},
            },
        }
