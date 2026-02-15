"""Shared fixtures for portfolio allocation tests."""

import pytest


@pytest.fixture()
def sample_initiatives():
    """Standard set of initiatives for testing."""
    return [
        {"id": "A", "cost": 4, "R_best": 15, "R_med": 10, "R_worst": 2, "confidence": 0.9},
        {"id": "B", "cost": 3, "R_best": 12, "R_med": 8, "R_worst": 1, "confidence": 0.6},
        {"id": "C", "cost": 3, "R_best": 9, "R_med": 6, "R_worst": 2, "confidence": 0.8},
        {"id": "D", "cost": 2, "R_best": 7, "R_med": 5, "R_worst": 3, "confidence": 0.4},
        {"id": "E", "cost": 5, "R_best": 18, "R_med": 9, "R_worst": 0, "confidence": 0.5},
    ]


@pytest.fixture()
def sample_event(sample_initiatives):
    """Orchestrator-shaped event with field mapping applied."""
    initiatives = [
        {
            "initiative_id": i["id"],
            "cost": i["cost"],
            "return_best": i["R_best"],
            "return_median": i["R_med"],
            "return_worst": i["R_worst"],
            "confidence": i["confidence"],
        }
        for i in sample_initiatives
    ]
    return {"initiatives": initiatives, "budget": 10}
