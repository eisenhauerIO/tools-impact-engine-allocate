"""Portfolio allocation solvers.

Provides decision-rule implementations for portfolio selection, a shared
preprocessing pipeline, and the ``AllocationSolver`` protocol that all
rules satisfy.

Convenience function ``solve_minimax_regret`` wraps preprocessing + the
minimax regret solver in a single call for backward compatibility and
standalone usage.
"""

from collections.abc import Callable
from typing import Any

from portfolio_allocation.solver._common import (
    SCENARIOS,
    calculate_effective_returns,
    calculate_gamma,
    empty_solver_result,
    extract_selection,
    preprocess,
)
from portfolio_allocation.solver._types import AllocationSolver, SolverResult
from portfolio_allocation.solver.bayesian import BayesianSolver
from portfolio_allocation.solver.minimax_regret import MinimaxRegretSolver

__all__ = [
    "AllocationSolver",
    "BayesianSolver",
    "MinimaxRegretSolver",
    "SCENARIOS",
    "SolverResult",
    "calculate_effective_returns",
    "calculate_gamma",
    "empty_solver_result",
    "extract_selection",
    "preprocess",
    "solve_minimax_regret",
]


def solve_minimax_regret(
    initiatives_data: list[dict[str, Any]],
    total_budget: float,
    min_confidence_threshold: float = 0.0,
    min_portfolio_worst_return: float = 0.0,
    confidence_penalty_func: Callable[[float], float] = calculate_gamma,
) -> SolverResult:
    """Preprocess and solve the minimax regret problem in one call.

    Convenience wrapper that filters by confidence, computes effective
    returns, and delegates to :class:`MinimaxRegretSolver`.

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
    SolverResult
    """
    processed = preprocess(initiatives_data, min_confidence_threshold, confidence_penalty_func)
    if not processed:
        return empty_solver_result("No Eligible Initiatives", "minimax_regret")
    solver = MinimaxRegretSolver()
    return solver(processed, total_budget, min_portfolio_worst_return)
