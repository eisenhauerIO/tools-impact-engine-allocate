"""Parse-once configuration for the allocation subsystem."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_KNOWN_RULES = {"minimax_regret", "bayesian"}
_CONFIG_FIELDS = {"budget", "costs", "rule", "min_confidence_threshold", "min_portfolio_worst_return"}


@dataclass
class AllocationConfig:
    """Validated allocation configuration.

    Parameters
    ----------
    budget : float
        Total budget for the portfolio (must be > 0).
    costs : dict[str, float]
        Per-initiative cost_to_scale mapping.
    rule : str
        Decision rule identifier (``"minimax_regret"`` or ``"bayesian"``).
    min_confidence_threshold : float
        Initiatives below this confidence are excluded.
    min_portfolio_worst_return : float
        Minimum aggregate worst-case return for the portfolio.
    solver_kwargs : dict
        Extra keyword arguments forwarded to the decision rule constructor
        (e.g. ``{"weights": {"best": 0.33, "med": 0.33, "worst": 0.34}}``).
    """

    budget: float
    costs: dict[str, float] = field(default_factory=dict)
    rule: str = "minimax_regret"
    min_confidence_threshold: float = 0.0
    min_portfolio_worst_return: float = 0.0
    solver_kwargs: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.budget <= 0:
            raise ValueError(f"budget must be > 0, got {self.budget}")
        if self.rule not in _KNOWN_RULES:
            raise ValueError(f"rule must be one of {sorted(_KNOWN_RULES)}, got {self.rule!r}")
        if not (0 <= self.min_confidence_threshold <= 1):
            raise ValueError(f"min_confidence_threshold must be in [0, 1], got {self.min_confidence_threshold}")
        if not self.costs:
            raise ValueError("costs must be a non-empty dict mapping initiative IDs to costs")


def load_config(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Load allocation configuration from a YAML file or dict.

    Parameters
    ----------
    source : str | Path | dict
        A path to a YAML file or a raw dict. YAML files must contain an
        ``allocation:`` section.

    Returns
    -------
    dict
        Fully validated configuration dictionary.

    Raises
    ------
    ValueError
        If required fields are missing or invalid.
    FileNotFoundError
        If the YAML file does not exist.
    """
    if isinstance(source, dict):
        raw = source
    else:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")
        raw = _load_yaml(path)

    section = raw.get("allocation", raw)

    known_keys = section.keys() & _CONFIG_FIELDS
    extra_keys = section.keys() - _CONFIG_FIELDS
    solver_kwargs = {k: section[k] for k in extra_keys}

    config_kwargs: dict[str, Any] = {k: section[k] for k in known_keys}
    config_kwargs["solver_kwargs"] = solver_kwargs

    cfg = AllocationConfig(**config_kwargs)
    return dataclasses.asdict(cfg)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file using PyYAML."""
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}
