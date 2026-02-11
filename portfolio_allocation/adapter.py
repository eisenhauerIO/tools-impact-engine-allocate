"""ALLOCATE component: minimax regret portfolio optimization."""

import logging
from dataclasses import asdict, dataclass
from typing import Any

from portfolio_allocation.solver import solve_minimax_regret

logger = logging.getLogger(__name__)

try:
    from impact_engine_orchestrator.components.base import PipelineComponent
    from impact_engine_orchestrator.contracts.allocate import AllocateResult
except ImportError:
    from abc import ABC, abstractmethod

    class PipelineComponent(ABC):  # type: ignore[no-redef]
        """Fallback base when orchestrator is not installed."""

        @abstractmethod
        def execute(self, event: dict) -> dict:
            """Process event and return result."""

    @dataclass
    class AllocateResult:  # type: ignore[no-redef]
        """Fallback contract when orchestrator is not installed."""

        selected_initiatives: list[str]
        predicted_returns: dict[str, float]
        budget_allocated: dict[str, float]


_FIELD_MAP_IN: dict[str, str] = {
    "initiative_id": "id",
    "return_best": "R_best",
    "return_median": "R_med",
    "return_worst": "R_worst",
}


def _to_solver_format(initiative: dict[str, Any]) -> dict[str, Any]:
    """Map an orchestrator initiative dict to solver field names.

    Parameters
    ----------
    initiative : dict[str, Any]
        Initiative dict with orchestrator field names.

    Returns
    -------
    dict[str, Any]
        Initiative dict with solver field names.
    """
    return {_FIELD_MAP_IN.get(key, key): value for key, value in initiative.items()}


class MinimaxRegretAllocate(PipelineComponent):
    """Select initiatives via minimax regret optimization.

    Wraps the PuLP/CBC-based minimax regret solver as a ``PipelineComponent``
    for the impact engine orchestrator.

    Parameters
    ----------
    min_confidence_threshold : float
        Initiatives below this confidence are excluded before optimization.
    min_portfolio_worst_return : float
        Minimum aggregate worst-case return constraint.
    """

    def __init__(
        self,
        min_confidence_threshold: float = 0.0,
        min_portfolio_worst_return: float = 0.0,
    ) -> None:
        self.min_confidence_threshold = min_confidence_threshold
        self.min_portfolio_worst_return = min_portfolio_worst_return

    def execute(self, event: dict) -> dict:
        """Run minimax regret allocation and return an ``AllocateResult`` dict.

        Parameters
        ----------
        event : dict
            Must contain ``initiatives`` (list of dicts with orchestrator
            field names) and ``budget`` (float).

        Returns
        -------
        dict
            Serialized ``AllocateResult`` with ``selected_initiatives``,
            ``predicted_returns``, and ``budget_allocated``.
        """
        initiatives = event["initiatives"]
        budget = event["budget"]

        solver_initiatives = [_to_solver_format(i) for i in initiatives]
        id_to_initiative = {i["initiative_id"]: i for i in initiatives}

        solver_result = solve_minimax_regret(
            initiatives_data=solver_initiatives,
            total_budget=budget,
            min_confidence_threshold=self.min_confidence_threshold,
            min_portfolio_worst_return=self.min_portfolio_worst_return,
        )

        logger.info(
            "Allocation complete: status=%s, selected=%d initiatives",
            solver_result["status"],
            len(solver_result["selected_initiatives"]),
        )

        selected_ids = solver_result["selected_initiatives"]

        result = AllocateResult(
            selected_initiatives=selected_ids,
            predicted_returns={sid: id_to_initiative[sid]["return_median"] for sid in selected_ids},
            budget_allocated={sid: id_to_initiative[sid]["cost"] for sid in selected_ids},
        )
        return asdict(result)
