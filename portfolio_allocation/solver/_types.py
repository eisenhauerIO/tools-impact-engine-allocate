"""Type definitions for the solver protocol and result contract."""

from typing import Any, Protocol, TypedDict


class SolverResult(TypedDict):
    """Common output contract all decision rules must satisfy.

    Parameters
    ----------
    status : str
        Solver termination status (e.g. ``"Optimal"``).
    selected_initiatives : list[str]
        IDs of selected initiatives.
    total_cost : float
        Aggregate cost of the selected portfolio.
    objective_value : float | None
        Value of the rule's objective function, or ``None`` if non-optimal.
    total_actual_returns : dict[str, float]
        Per-scenario effective returns for the selected portfolio.
    rule : str
        Identifier for the decision rule (e.g. ``"minimax_regret"``).
    detail : dict[str, Any]
        Rule-specific diagnostics, opaque to the adapter.
    """

    status: str
    selected_initiatives: list[str]
    total_cost: float
    objective_value: float | None
    total_actual_returns: dict[str, float]
    rule: str
    detail: dict[str, Any]


class AllocationSolver(Protocol):
    """Protocol for decision-rule solvers.

    Implementations receive preprocessed initiatives (with ``effective_returns``
    already computed) and return a :class:`SolverResult`.
    """

    def __call__(
        self,
        initiatives: list[dict[str, Any]],
        total_budget: float,
        min_portfolio_worst_return: float,
    ) -> SolverResult: ...
