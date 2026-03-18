"""Portfolio allocation rules.

Provides decision-rule implementations for portfolio selection, a shared
preprocessing pipeline, and the ``AllocationRule`` protocol that all
rules satisfy.

The ``allocate()`` facade loads config and data, then dispatches to the
appropriate rule.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from impact_engine_allocate.allocation._common import (
    SCENARIOS,
    calculate_effective_returns,
    calculate_gamma,
    empty_rule_result,
    extract_selection,
    preprocess,
)
from impact_engine_allocate.allocation._types import AllocationRule, RuleResult
from impact_engine_allocate.allocation.bayesian import BayesianAllocation
from impact_engine_allocate.allocation.minimax_regret import MinimaxRegretAllocation

__all__ = [
    "AllocationRule",
    "BayesianAllocation",
    "MinimaxRegretAllocation",
    "RuleResult",
    "SCENARIOS",
    "allocate_portfolio",
    "calculate_effective_returns",
    "calculate_gamma",
    "empty_rule_result",
    "extract_selection",
    "preprocess",
]

_ALLOCATION_REGISTRY: dict[str, type] = {
    "minimax_regret": MinimaxRegretAllocation,
    "bayesian": BayesianAllocation,
}


def allocate_portfolio(
    config: str | Path | dict[str, Any],
    data_dir: str | Path,
) -> RuleResult:
    """Run portfolio allocation end-to-end.

    Loads configuration, reads initiative data from job directories,
    preprocesses, and dispatches to the configured decision rule.

    Parameters
    ----------
    config : str | Path | dict
        Path to a YAML config file or a raw config dict. Must contain
        an ``allocation:`` section with ``budget`` and ``costs``.
    data_dir : str | Path
        Root directory containing per-initiative subdirectories with
        ``impact_results.json`` and ``evaluate_result.json``.

    Returns
    -------
    RuleResult
        Portfolio selection result from the decision rule.
    """
    from impact_engine_allocate.config import load_config
    from impact_engine_allocate.job_reader import load_initiatives

    cfg = load_config(config)

    initiatives = load_initiatives(data_dir, cfg["costs"])

    processed = preprocess(initiatives, cfg["min_confidence_threshold"])
    if not processed:
        return empty_rule_result("No Eligible Initiatives", cfg["rule"])

    rule_cls = _ALLOCATION_REGISTRY[cfg["rule"]]
    rule = rule_cls(**cfg["solver_kwargs"])
    return rule(processed, cfg["budget"], cfg["min_portfolio_worst_return"])
