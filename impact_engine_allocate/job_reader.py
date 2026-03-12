"""Job directory reader for the allocation subsystem.

Reads initiative data from pipeline output directories (``impact_results.json``
and ``evaluate_result.json``) and converts them into the flat dict format
expected by the allocation rules.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _resolve_param_key(treatment_var: str, params: dict) -> str:
    """Find the statsmodels coefficient key for a treatment variable.

    Statsmodels encodes categoricals as e.g. ``enriched[T.True]``.
    Returns an exact match first, then falls back to prefix matching.
    """
    if treatment_var in params:
        return treatment_var
    matches = [k for k in params if k.startswith(f"{treatment_var}[")]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"Treatment variable {treatment_var!r} not found in params: {list(params.keys())}")


def _extract_estimates(result: dict[str, Any]) -> dict[str, Any]:
    """Extract effect_estimate, ci_lower, ci_upper from model-specific output.

    Parameters
    ----------
    result : dict
        Full ``impact_results.json`` content (nested model-specific envelope).

    Returns
    -------
    dict
        Flat dict with ``effect_estimate``, ``ci_lower``, ``ci_upper``.

    Raises
    ------
    ValueError
        If the model type is unknown.
    """
    model_type = result["model_type"]
    estimates = result["data"]["impact_estimates"]

    if model_type == "experiment":
        formula = result["data"]["model_params"]["formula"]
        treatment_var = formula.split("~")[1].strip().split("+")[0].strip()
        key = _resolve_param_key(treatment_var, estimates["params"])
        return {
            "effect_estimate": estimates["params"][key],
            "ci_lower": estimates["conf_int"][key][0],
            "ci_upper": estimates["conf_int"][key][1],
        }

    if model_type == "synthetic_control":
        return {
            "effect_estimate": estimates["att"],
            "ci_lower": estimates["ci_lower"],
            "ci_upper": estimates["ci_upper"],
        }

    if model_type == "nearest_neighbour_matching":
        att = estimates["att"]
        att_se = estimates["att_se"]
        return {
            "effect_estimate": att,
            "ci_lower": att - 1.96 * att_se,
            "ci_upper": att + 1.96 * att_se,
        }

    if model_type == "interrupted_time_series":
        effect = estimates["intervention_effect"]
        return {
            "effect_estimate": effect,
            "ci_lower": effect,
            "ci_upper": effect,
        }

    if model_type == "subclassification":
        effect = estimates["treatment_effect"]
        return {
            "effect_estimate": effect,
            "ci_lower": effect,
            "ci_upper": effect,
        }

    if model_type == "metrics_approximation":
        effect = estimates["impact"]
        return {
            "effect_estimate": effect,
            "ci_lower": effect,
            "ci_upper": effect,
        }

    raise ValueError(f"Unknown model_type: {model_type!r}")


def load_initiatives(
    data_dir: str | Path,
    costs: dict[str, float],
) -> list[dict[str, Any]]:
    """Load initiative data from pipeline output directories.

    Scans ``data_dir`` for subdirectories, each representing one initiative.
    Reads ``impact_results.json`` (measure output) and ``evaluate_result.json``
    (evaluate output) from each subdirectory.

    Parameters
    ----------
    data_dir : str | Path
        Root directory containing per-initiative subdirectories.
    costs : dict[str, float]
        Mapping from initiative ID (directory name) to cost_to_scale.

    Returns
    -------
    list[dict[str, Any]]
        List of initiative dicts with keys ``id``, ``cost``, ``R_best``,
        ``R_med``, ``R_worst``, ``confidence``.

    Raises
    ------
    FileNotFoundError
        If required files are missing from an initiative directory.
    ValueError
        If an initiative directory has no matching cost entry.
    """
    data_dir = Path(data_dir)
    initiatives = []

    for subdir in sorted(data_dir.iterdir()):
        if not subdir.is_dir():
            continue

        initiative_id = subdir.name

        if initiative_id not in costs:
            raise ValueError(f"No cost entry for initiative {initiative_id!r} in costs dict")

        impact_path = subdir / "impact_results.json"
        evaluate_path = subdir / "evaluate_result.json"

        if not impact_path.exists():
            raise FileNotFoundError(f"impact_results.json not found in {subdir}")
        if not evaluate_path.exists():
            raise FileNotFoundError(f"evaluate_result.json not found in {subdir}")

        with open(impact_path, encoding="utf-8") as fh:
            impact_data = json.load(fh)

        with open(evaluate_path, encoding="utf-8") as fh:
            evaluate_data = json.load(fh)

        extracted = _extract_estimates(impact_data)

        initiatives.append(
            {
                "id": initiative_id,
                "cost": costs[initiative_id],
                "R_best": extracted["ci_upper"],
                "R_med": extracted["effect_estimate"],
                "R_worst": extracted["ci_lower"],
                "confidence": evaluate_data["confidence"],
            }
        )

        logger.debug("Loaded initiative %s from %s", initiative_id, subdir)

    return initiatives
