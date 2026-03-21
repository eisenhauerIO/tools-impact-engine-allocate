"""Portfolio allocation rules.

Provides decision-rule implementations for portfolio selection, a shared
preprocessing pipeline, and the ``AllocationRule`` protocol that all
rules satisfy.

The ``allocate()`` facade loads config and data, then dispatches to the
appropriate rule.
"""

from __future__ import annotations

import json
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
from impact_engine_allocate.allocation._types import AllocationRule, RuleRegistry, RuleResult
from impact_engine_allocate.allocation.bayesian import BayesianAllocation
from impact_engine_allocate.allocation.minimax_regret import MinimaxRegretAllocation

ALLOCATE_RESULT_FILENAME = "allocate_result.json"

__all__ = [
    "ALLOCATE_RESULT_FILENAME",
    "AllocationRule",
    "BayesianAllocation",
    "MinimaxRegretAllocation",
    "RuleRegistry",
    "RuleResult",
    "RULE_REGISTRY",
    "SCENARIOS",
    "allocate_portfolio",
    "calculate_effective_returns",
    "calculate_gamma",
    "empty_rule_result",
    "extract_selection",
    "preprocess",
]

from impact_engine_allocate.allocation._types import RULE_REGISTRY  # noqa: E402

RULE_REGISTRY.register("minimax_regret", MinimaxRegretAllocation)
RULE_REGISTRY.register("bayesian", BayesianAllocation)


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
    init_by_id = {i["id"]: i for i in initiatives}

    processed = preprocess(initiatives, cfg["min_confidence_threshold"])
    if not processed:
        solver_result = empty_rule_result("No Eligible Initiatives", cfg["rule"])
    else:
        rule_cls = RULE_REGISTRY.get_class(cfg["rule"])
        rule = rule_cls(**cfg["solver_kwargs"])
        solver_result = rule(processed, cfg["budget"], cfg["min_portfolio_worst_return"])

    selected_ids = solver_result["selected_initiatives"]

    allocate_result = {
        "selected_initiatives": selected_ids,
        "predicted_returns": {sid: init_by_id[sid]["R_med"] for sid in selected_ids},
        "budget_allocated": {sid: init_by_id[sid]["cost"] for sid in selected_ids},
        "solver_detail": {
            "rule": solver_result["rule"],
            "objective_value": solver_result["objective_value"],
            "total_actual_returns": solver_result["total_actual_returns"],
            "detail": solver_result["detail"],
        },
    }

    result_path = Path(data_dir) / ALLOCATE_RESULT_FILENAME
    result_path.write_text(json.dumps(allocate_result, indent=2) + "\n", encoding="utf-8")

    return solver_result
