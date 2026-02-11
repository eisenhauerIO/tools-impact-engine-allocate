"""Unit tests for the minimax regret solver."""

import copy

import pytest

from portfolio_allocation.solver import (
    calculate_effective_returns,
    calculate_gamma,
    solve_minimax_regret,
)

SOLVE_DEFAULTS = {
    "total_budget": 10,
    "min_confidence_threshold": 0.0,
    "min_portfolio_worst_return": 0.0,
}


class TestCalculateGamma:
    def test_zero_confidence(self):
        assert calculate_gamma(0.0) == 1.0

    def test_full_confidence(self):
        assert calculate_gamma(1.0) == 0.0

    def test_mid_confidence(self):
        assert calculate_gamma(0.5) == pytest.approx(0.5)

    def test_high_confidence(self):
        assert calculate_gamma(0.9) == pytest.approx(0.1)

    def test_below_range_raises(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            calculate_gamma(-0.1)

    def test_above_range_raises(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            calculate_gamma(1.1)


class TestCalculateEffectiveReturns:
    def test_no_mutation(self, sample_initiatives):
        original = copy.deepcopy(sample_initiatives)
        calculate_effective_returns(sample_initiatives)
        assert sample_initiatives == original

    def test_returns_new_list(self, sample_initiatives):
        result = calculate_effective_returns(sample_initiatives)
        assert result is not sample_initiatives
        for orig, new in zip(sample_initiatives, result):
            assert new is not orig

    def test_gamma_added(self, sample_initiatives):
        result = calculate_effective_returns(sample_initiatives)
        for item in result:
            assert "gamma" in item
            assert "effective_returns" in item

    def test_full_confidence_no_penalty(self):
        initiatives = [{"id": "X", "cost": 1, "R_best": 10, "R_med": 5, "R_worst": 1, "confidence": 1.0}]
        result = calculate_effective_returns(initiatives)
        eff = result[0]["effective_returns"]
        assert eff["best"] == pytest.approx(10.0)
        assert eff["med"] == pytest.approx(5.0)
        assert eff["worst"] == pytest.approx(1.0)

    def test_zero_confidence_all_worst(self):
        initiatives = [{"id": "X", "cost": 1, "R_best": 10, "R_med": 5, "R_worst": 1, "confidence": 0.0}]
        result = calculate_effective_returns(initiatives)
        eff = result[0]["effective_returns"]
        assert eff["best"] == pytest.approx(1.0)
        assert eff["med"] == pytest.approx(1.0)
        assert eff["worst"] == pytest.approx(1.0)

    def test_custom_penalty_func(self):
        initiatives = [{"id": "X", "cost": 1, "R_best": 10, "R_med": 5, "R_worst": 2, "confidence": 0.8}]
        result = calculate_effective_returns(initiatives, confidence_penalty_func=lambda c: 0.0)
        eff = result[0]["effective_returns"]
        assert eff["best"] == pytest.approx(10.0)
        assert eff["med"] == pytest.approx(5.0)


class TestSolveMinimax:
    def test_optimal_status(self, sample_initiatives):
        result = solve_minimax_regret(sample_initiatives, **{**SOLVE_DEFAULTS, "min_confidence_threshold": 0.5})
        assert result["status"] == "Optimal"

    def test_budget_constraint_respected(self, sample_initiatives):
        budget = 10
        result = solve_minimax_regret(sample_initiatives, **{**SOLVE_DEFAULTS, "total_budget": budget})
        assert result["total_cost"] <= budget

    def test_confidence_filtering(self, sample_initiatives):
        result = solve_minimax_regret(sample_initiatives, **{**SOLVE_DEFAULTS, "min_confidence_threshold": 0.5})
        low_conf_ids = {i["id"] for i in sample_initiatives if i["confidence"] < 0.5}
        assert not low_conf_ids.intersection(result["selected_initiatives"])

    def test_determinism(self, sample_initiatives):
        kwargs = {**SOLVE_DEFAULTS, "min_confidence_threshold": 0.5}
        r1 = solve_minimax_regret(sample_initiatives, **kwargs)
        r2 = solve_minimax_regret(sample_initiatives, **kwargs)
        assert r1["selected_initiatives"] == r2["selected_initiatives"]
        assert r1["min_max_regret"] == pytest.approx(r2["min_max_regret"])

    def test_single_initiative(self):
        initiatives = [{"id": "only", "cost": 5, "R_best": 10, "R_med": 7, "R_worst": 3, "confidence": 0.9}]
        result = solve_minimax_regret(initiatives, **SOLVE_DEFAULTS)
        assert result["status"] == "Optimal"
        assert result["selected_initiatives"] == ["only"]

    def test_zero_budget(self, sample_initiatives):
        result = solve_minimax_regret(sample_initiatives, **{**SOLVE_DEFAULTS, "total_budget": 0})
        assert result["selected_initiatives"] == []

    def test_all_filtered_by_confidence(self, sample_initiatives):
        result = solve_minimax_regret(sample_initiatives, **{**SOLVE_DEFAULTS, "min_confidence_threshold": 1.0})
        assert result["status"] == "No Eligible Initiatives"
        assert result["selected_initiatives"] == []

    def test_all_same_confidence(self):
        initiatives = [
            {"id": "A", "cost": 3, "R_best": 10, "R_med": 7, "R_worst": 2, "confidence": 0.7},
            {"id": "B", "cost": 3, "R_best": 9, "R_med": 6, "R_worst": 3, "confidence": 0.7},
            {"id": "C", "cost": 3, "R_best": 8, "R_med": 5, "R_worst": 4, "confidence": 0.7},
        ]
        result = solve_minimax_regret(initiatives, **{**SOLVE_DEFAULTS, "total_budget": 6})
        assert result["status"] == "Optimal"
        assert len(result["selected_initiatives"]) <= 2

    def test_result_keys(self, sample_initiatives):
        result = solve_minimax_regret(sample_initiatives, **SOLVE_DEFAULTS)
        expected_keys = {
            "status",
            "min_max_regret",
            "selected_initiatives",
            "total_cost",
            "total_actual_returns",
            "v_j_star",
            "regrets_for_selected_portfolio",
        }
        assert set(result.keys()) == expected_keys

    def test_selected_are_subset_of_input(self, sample_initiatives):
        result = solve_minimax_regret(sample_initiatives, **SOLVE_DEFAULTS)
        input_ids = {i["id"] for i in sample_initiatives}
        assert set(result["selected_initiatives"]).issubset(input_ids)
