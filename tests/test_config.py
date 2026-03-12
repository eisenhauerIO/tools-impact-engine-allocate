"""Tests for allocation config loading and validation."""

import pytest

from impact_engine_allocate.config import AllocationConfig, load_config


class TestAllocationConfig:
    def test_valid_config(self):
        cfg = AllocationConfig(budget=100, costs={"A": 10})
        assert cfg.budget == 100
        assert cfg.rule == "minimax_regret"

    def test_budget_must_be_positive(self):
        with pytest.raises(ValueError, match="budget must be > 0"):
            AllocationConfig(budget=0, costs={"A": 10})

    def test_negative_budget_raises(self):
        with pytest.raises(ValueError, match="budget must be > 0"):
            AllocationConfig(budget=-5, costs={"A": 10})

    def test_invalid_rule(self):
        with pytest.raises(ValueError, match="rule must be one of"):
            AllocationConfig(budget=100, costs={"A": 10}, rule="unknown")

    def test_threshold_out_of_range(self):
        with pytest.raises(ValueError, match="min_confidence_threshold"):
            AllocationConfig(budget=100, costs={"A": 10}, min_confidence_threshold=1.5)

    def test_empty_costs_raises(self):
        with pytest.raises(ValueError, match="costs must be a non-empty"):
            AllocationConfig(budget=100)

    def test_bayesian_rule(self):
        cfg = AllocationConfig(budget=100, costs={"A": 10}, rule="bayesian")
        assert cfg.rule == "bayesian"


class TestLoadConfig:
    def test_from_dict(self):
        raw = {"allocation": {"budget": 100, "costs": {"A": 10, "B": 20}}}
        cfg = load_config(raw)
        assert cfg["budget"] == 100
        assert cfg["costs"] == {"A": 10, "B": 20}
        assert cfg["rule"] == "minimax_regret"

    def test_from_dict_without_section(self):
        raw = {"budget": 100, "costs": {"A": 10}}
        cfg = load_config(raw)
        assert cfg["budget"] == 100

    def test_from_yaml_file(self, tmp_path):
        yaml_content = "allocation:\n  budget: 200\n  costs:\n    X: 50\n  rule: minimax_regret\n"
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)
        cfg = load_config(str(config_file))
        assert cfg["budget"] == 200
        assert cfg["costs"] == {"X": 50}

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_extra_keys_go_to_solver_kwargs(self):
        raw = {
            "allocation": {
                "budget": 100,
                "costs": {"A": 10},
                "rule": "bayesian",
                "weights": {"best": 0.33, "med": 0.33, "worst": 0.34},
            }
        }
        cfg = load_config(raw)
        assert cfg["solver_kwargs"] == {"weights": {"best": 0.33, "med": 0.33, "worst": 0.34}}

    def test_invalid_budget_in_dict(self):
        with pytest.raises(ValueError, match="budget must be > 0"):
            load_config({"allocation": {"budget": -1, "costs": {"A": 10}}})
