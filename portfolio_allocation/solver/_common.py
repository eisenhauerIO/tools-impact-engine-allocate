"""Shared utilities for portfolio allocation solvers.

Contains preprocessing (confidence filtering, effective return computation),
result extraction from PuLP variables, and the default confidence penalty.
"""

import logging
from collections.abc import Callable
from typing import Any

import pulp as lp

from portfolio_allocation.solver._types import SolverResult

logger = logging.getLogger(__name__)

SCENARIOS = ["best", "med", "worst"]


def calculate_gamma(confidence_score: float) -> float:
    """Convert a confidence score to a penalty factor.

    Parameters
    ----------
    confidence_score : float
        Confidence in the initiative's estimates, between 0 and 1.

    Returns
    -------
    float
        Penalty factor gamma = 1 - confidence.

    Raises
    ------
    ValueError
        If confidence_score is outside [0, 1].
    """
    if not (0 <= confidence_score <= 1):
        raise ValueError("Confidence score must be between 0 and 1.")
    return 1 - confidence_score


def calculate_effective_returns(
    initiatives: list[dict[str, Any]],
    confidence_penalty_func: Callable[[float], float] = calculate_gamma,
) -> list[dict[str, Any]]:
    """Calculate confidence-penalized effective returns for each initiative.

    Blends each scenario's base return toward the worst-case return,
    weighted by the penalty factor gamma. Does not mutate input.

    Parameters
    ----------
    initiatives : list[dict[str, Any]]
        Each dict must have keys: ``confidence``, ``R_best``, ``R_med``,
        ``R_worst``.
    confidence_penalty_func : Callable[[float], float], optional
        Maps confidence to penalty factor gamma. Default: ``1 - confidence``.

    Returns
    -------
    list[dict[str, Any]]
        New list of dicts, each augmented with ``gamma`` and
        ``effective_returns`` keys.
    """
    result = []
    for initiative in initiatives:
        c_i = initiative["confidence"]
        gamma_i = confidence_penalty_func(c_i)
        r_base_map = {
            "best": initiative["R_best"],
            "med": initiative["R_med"],
            "worst": initiative["R_worst"],
        }
        effective_returns = {}
        for scenario_name in SCENARIOS:
            r_ij_base = r_base_map[scenario_name]
            effective_returns[scenario_name] = (1 - gamma_i) * r_ij_base + gamma_i * initiative["R_worst"]
        result.append({**initiative, "gamma": gamma_i, "effective_returns": effective_returns})
    return result


def preprocess(
    initiatives: list[dict[str, Any]],
    min_confidence_threshold: float = 0.0,
    confidence_penalty_func: Callable[[float], float] = calculate_gamma,
) -> list[dict[str, Any]]:
    """Filter initiatives by confidence and compute effective returns.

    Parameters
    ----------
    initiatives : list[dict[str, Any]]
        Raw initiatives with solver field names.
    min_confidence_threshold : float
        Initiatives below this confidence are excluded.
    confidence_penalty_func : Callable[[float], float], optional
        Maps confidence to penalty factor gamma.

    Returns
    -------
    list[dict[str, Any]]
        Preprocessed initiatives with ``effective_returns``, or empty list
        if no initiatives pass the confidence threshold.
    """
    eligible = [i for i in initiatives if i["confidence"] >= min_confidence_threshold]
    if not eligible:
        return []
    return calculate_effective_returns(eligible, confidence_penalty_func)


def extract_selection(
    x_vars: dict[str, lp.LpVariable],
    initiatives: list[dict[str, Any]],
    scenarios: list[str],
) -> tuple[list[str], float, dict[str, float]]:
    """Extract selected initiatives and aggregate returns from a solved BIP.

    Parameters
    ----------
    x_vars : dict[str, LpVariable]
        Binary selection variables keyed by initiative ID.
    initiatives : list[dict[str, Any]]
        Preprocessed initiatives with ``effective_returns``.
    scenarios : list[str]
        Scenario names to aggregate over.

    Returns
    -------
    tuple[list[str], float, dict[str, float]]
        ``(selected_ids, total_cost, total_actual_returns)``.
    """
    selected: list[str] = []
    total_cost = 0.0
    total_returns = {s: 0.0 for s in scenarios}
    for i in initiatives:
        if x_vars[i["id"]].varValue > 0.5:
            selected.append(i["id"])
            total_cost += i["cost"]
            for s in scenarios:
                total_returns[s] += i["effective_returns"][s]
    return selected, total_cost, total_returns


def empty_solver_result(status: str, rule: str, scenarios: list[str] | None = None) -> SolverResult:
    """Build a ``SolverResult`` with no selection.

    Parameters
    ----------
    status : str
        Descriptive status string.
    rule : str
        Decision rule identifier.
    scenarios : list[str], optional
        Scenario names for the empty returns dict. Defaults to ``SCENARIOS``.

    Returns
    -------
    SolverResult
    """
    if scenarios is None:
        scenarios = SCENARIOS
    return {
        "status": status,
        "selected_initiatives": [],
        "total_cost": 0.0,
        "objective_value": None,
        "total_actual_returns": {s: 0.0 for s in scenarios},
        "rule": rule,
        "detail": {},
    }
