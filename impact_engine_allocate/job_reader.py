"""Job directory reader for the allocation subsystem.

Reads initiative data from pipeline output directories (``measure_result.json``
and ``evaluate_result.json``) and converts them into the flat dict format
expected by the allocation rules.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_initiatives(
    data_dir: str | Path,
    costs: dict[str, float],
) -> list[dict[str, Any]]:
    """Load initiative data from pipeline output directories.

    Scans ``data_dir`` for subdirectories, each representing one initiative.
    Reads ``measure_result.json`` (measure output) and ``evaluate_result.json``
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

        measure_path = subdir / "measure_result.json"
        evaluate_path = subdir / "evaluate_result.json"

        if not measure_path.exists():
            raise FileNotFoundError(f"measure_result.json not found in {subdir}")
        if not evaluate_path.exists():
            raise FileNotFoundError(f"evaluate_result.json not found in {subdir}")

        with open(measure_path, encoding="utf-8") as fh:
            measure_data = json.load(fh)

        with open(evaluate_path, encoding="utf-8") as fh:
            evaluate_data = json.load(fh)

        initiatives.append(
            {
                "id": initiative_id,
                "cost": costs[initiative_id],
                "R_best": measure_data["ci_upper"],
                "R_med": measure_data["effect_estimate"],
                "R_worst": measure_data["ci_lower"],
                "confidence": evaluate_data["confidence"],
            }
        )

        logger.debug("Loaded initiative %s from %s", initiative_id, subdir)

    return initiatives
