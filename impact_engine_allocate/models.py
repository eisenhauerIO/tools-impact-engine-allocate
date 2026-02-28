"""Data models for the ALLOCATE pipeline stage."""

from dataclasses import dataclass


@dataclass
class AllocateResult:
    """Portfolio selection with budget allocation.

    Parameters
    ----------
    selected_initiatives : list[str]
        Initiative IDs chosen for investment.
    predicted_returns : dict[str, float]
        Predicted return for each selected initiative.
    budget_allocated : dict[str, float]
        Budget allocated to each selected initiative.
    """

    selected_initiatives: list[str]
    predicted_returns: dict[str, float]
    budget_allocated: dict[str, float]

    def __post_init__(self) -> None:
        """Validate that return and budget dicts are consistent with selected initiatives."""
        selected = set(self.selected_initiatives)
        if set(self.predicted_returns) != selected:
            raise ValueError("predicted_returns keys must match selected_initiatives")
        if set(self.budget_allocated) != selected:
            raise ValueError("budget_allocated keys must match selected_initiatives")
