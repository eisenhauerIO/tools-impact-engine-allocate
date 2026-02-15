"""Unit tests for the Bayesian (weighted-scenario) decision rule."""

import pytest

from impact_engine_allocate.solver import BayesianSolver, preprocess

WEIGHTS_EQUAL = {"best": 1 / 3, "med": 1 / 3, "worst": 1 / 3}
WEIGHTS_PESSIMISTIC = {"best": 0.1, "med": 0.3, "worst": 0.6}


class TestBayesianSolverConstruction:
    def test_valid_weights(self):
        solver = BayesianSolver(weights=WEIGHTS_EQUAL)
        assert solver.weights == pytest.approx(WEIGHTS_EQUAL)

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            BayesianSolver(weights={"best": -0.1, "med": 0.6, "worst": 0.5})

    def test_weights_not_summing_to_one_raises(self):
        with pytest.raises(ValueError, match="sum to 1"):
            BayesianSolver(weights={"best": 0.5, "med": 0.5, "worst": 0.5})


class TestBayesianSolver:
    @pytest.fixture()
    def processed_initiatives(self, sample_initiatives):
        return preprocess(sample_initiatives)

    def test_optimal_status(self, processed_initiatives):
        solver = BayesianSolver(weights=WEIGHTS_EQUAL)
        result = solver(processed_initiatives, total_budget=10, min_portfolio_worst_return=0.0)
        assert result["status"] == "Optimal"

    def test_result_keys(self, processed_initiatives):
        solver = BayesianSolver(weights=WEIGHTS_EQUAL)
        result = solver(processed_initiatives, total_budget=10, min_portfolio_worst_return=0.0)
        expected_keys = {
            "status",
            "selected_initiatives",
            "total_cost",
            "objective_value",
            "total_actual_returns",
            "rule",
            "detail",
        }
        assert set(result.keys()) == expected_keys

    def test_rule_identifier(self, processed_initiatives):
        solver = BayesianSolver(weights=WEIGHTS_EQUAL)
        result = solver(processed_initiatives, total_budget=10, min_portfolio_worst_return=0.0)
        assert result["rule"] == "bayesian"

    def test_detail_contains_weights(self, processed_initiatives):
        solver = BayesianSolver(weights=WEIGHTS_EQUAL)
        result = solver(processed_initiatives, total_budget=10, min_portfolio_worst_return=0.0)
        assert "weights" in result["detail"]
        assert result["detail"]["weights"] == pytest.approx(WEIGHTS_EQUAL)

    def test_budget_constraint_respected(self, processed_initiatives):
        solver = BayesianSolver(weights=WEIGHTS_EQUAL)
        result = solver(processed_initiatives, total_budget=5, min_portfolio_worst_return=0.0)
        assert result["total_cost"] <= 5

    def test_determinism(self, processed_initiatives):
        solver = BayesianSolver(weights=WEIGHTS_EQUAL)
        r1 = solver(processed_initiatives, total_budget=10, min_portfolio_worst_return=0.0)
        r2 = solver(processed_initiatives, total_budget=10, min_portfolio_worst_return=0.0)
        assert r1["selected_initiatives"] == r2["selected_initiatives"]
        assert r1["objective_value"] == pytest.approx(r2["objective_value"])

    def test_pessimistic_weights_favor_safe_choices(self, processed_initiatives):
        optimistic = BayesianSolver(weights={"best": 0.8, "med": 0.1, "worst": 0.1})
        pessimistic = BayesianSolver(weights=WEIGHTS_PESSIMISTIC)
        r_opt = optimistic(processed_initiatives, total_budget=10, min_portfolio_worst_return=0.0)
        r_pes = pessimistic(processed_initiatives, total_budget=10, min_portfolio_worst_return=0.0)
        # Pessimistic portfolio should have higher worst-case return.
        worst_opt = r_opt["total_actual_returns"]["worst"]
        worst_pes = r_pes["total_actual_returns"]["worst"]
        assert worst_pes >= worst_opt or r_opt["selected_initiatives"] == r_pes["selected_initiatives"]

    def test_selected_are_subset_of_input(self, processed_initiatives):
        solver = BayesianSolver(weights=WEIGHTS_EQUAL)
        result = solver(processed_initiatives, total_budget=10, min_portfolio_worst_return=0.0)
        input_ids = {i["id"] for i in processed_initiatives}
        assert set(result["selected_initiatives"]).issubset(input_ids)
