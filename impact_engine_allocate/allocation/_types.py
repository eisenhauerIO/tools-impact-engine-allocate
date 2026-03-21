"""Type definitions for the allocation rule interface, registry, and result contract."""

from abc import ABC, abstractmethod
from typing import Any, TypedDict


class RuleResult(TypedDict):
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


class AllocationRule(ABC):
    """Abstract base class for decision-rule solvers.

    Subclass and implement :meth:`__call__` to provide a custom allocation
    decision rule. Register the subclass with :data:`RULE_REGISTRY` to make
    it available via string name in pipeline configs.
    """

    @abstractmethod
    def __call__(
        self,
        initiatives: list[dict[str, Any]],
        total_budget: float,
        min_portfolio_worst_return: float,
    ) -> RuleResult:
        """Process initiatives and return allocation result.

        Parameters
        ----------
        initiatives : list[dict]
            Preprocessed initiatives with ``effective_returns`` computed.
        total_budget : float
            Total capital available for allocation.
        min_portfolio_worst_return : float
            Minimum acceptable worst-case portfolio return.

        Returns
        -------
        RuleResult
        """


class RuleRegistry:
    """Registry mapping names to :class:`AllocationRule` subclasses.

    Example
    -------
    >>> class MyRule(AllocationRule):
    ...     def __call__(self, initiatives, total_budget, min_portfolio_worst_return):
    ...         ...
    >>> RULE_REGISTRY.register("my_rule", MyRule)
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[AllocationRule]] = {}

    def register(self, name: str, cls: type[AllocationRule]) -> None:
        """Register an allocation rule class under *name*.

        Parameters
        ----------
        name : str
            Registry key (used in pipeline configs as the ``rule`` field).
        cls : type[AllocationRule]
            Class to register. Must be a subclass of :class:`AllocationRule`.

        Raises
        ------
        ValueError
            If *cls* is not a subclass of :class:`AllocationRule`.
        """
        if not issubclass(cls, AllocationRule):
            raise ValueError(f"{cls.__name__} must be a subclass of AllocationRule")
        self._registry[name] = cls

    def get_class(self, name: str) -> type[AllocationRule]:
        """Return the rule class registered under *name*.

        Parameters
        ----------
        name : str
            Registered rule name.

        Returns
        -------
        type[AllocationRule]
            The rule class (not an instance — instantiate with desired kwargs).

        Raises
        ------
        ValueError
            If *name* is not registered.
        """
        if name not in self._registry:
            available = list(self._registry)
            raise ValueError(f"Unknown rule {name!r}. Available: {available}")
        return self._registry[name]

    def list(self) -> list[str]:
        """Return sorted list of registered rule names.

        Returns
        -------
        list[str]
        """
        return sorted(self._registry)


RULE_REGISTRY = RuleRegistry()
