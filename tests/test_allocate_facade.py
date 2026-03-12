"""End-to-end tests for the allocate() facade."""

import json

from impact_engine_allocate.allocation import allocate


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_experiment_results(effect=5.0, ci_lower=3.0, ci_upper=7.0):
    return {
        "model_type": "experiment",
        "data": {
            "impact_estimates": {
                "params": {"treatment": effect},
                "conf_int": {"treatment": [ci_lower, ci_upper]},
                "pvalues": {"treatment": 0.01},
            },
            "model_summary": {"nobs": 1000},
            "model_params": {"formula": "revenue ~ treatment"},
        },
        "metadata": {},
    }


def _make_evaluate_result(confidence=0.85):
    return {
        "initiative_id": "test",
        "confidence": confidence,
        "confidence_range": [0.7, 1.0],
        "strategy": "score",
        "report": "",
    }


def _setup_data_dir(tmp_path, initiatives):
    for name, conf in initiatives.items():
        d = tmp_path / name
        d.mkdir(parents=True)
        _write_json(d / "impact_results.json", _make_experiment_results(**conf.get("impact", {})))
        _write_json(d / "evaluate_result.json", _make_evaluate_result(conf.get("confidence", 0.85)))


class TestAllocateFacade:
    def test_basic_allocation(self, tmp_path):
        _setup_data_dir(tmp_path, {"A": {}, "B": {}})
        config = {
            "allocation": {
                "budget": 200,
                "costs": {"A": 50, "B": 60},
            }
        }
        result = allocate(config, tmp_path)
        assert result["status"] == "Optimal"
        assert set(result["selected_initiatives"]).issubset({"A", "B"})
        assert result["rule"] == "minimax_regret"

    def test_bayesian_rule(self, tmp_path):
        _setup_data_dir(tmp_path, {"A": {}, "B": {}})
        config = {
            "allocation": {
                "budget": 200,
                "costs": {"A": 50, "B": 60},
                "rule": "bayesian",
                "weights": {"best": 0.33, "med": 0.33, "worst": 0.34},
            }
        }
        result = allocate(config, tmp_path)
        assert result["status"] == "Optimal"
        assert result["rule"] == "bayesian"

    def test_confidence_filtering(self, tmp_path):
        _setup_data_dir(
            tmp_path,
            {"A": {"confidence": 0.9}, "B": {"confidence": 0.2}},
        )
        config = {
            "allocation": {
                "budget": 200,
                "costs": {"A": 50, "B": 60},
                "min_confidence_threshold": 0.5,
            }
        }
        result = allocate(config, tmp_path)
        assert "B" not in result["selected_initiatives"]

    def test_all_filtered_returns_empty(self, tmp_path):
        _setup_data_dir(tmp_path, {"A": {"confidence": 0.1}})
        config = {
            "allocation": {
                "budget": 200,
                "costs": {"A": 50},
                "min_confidence_threshold": 0.9,
            }
        }
        result = allocate(config, tmp_path)
        assert result["status"] == "No Eligible Initiatives"
        assert result["selected_initiatives"] == []

    def test_from_yaml_file(self, tmp_path):
        _setup_data_dir(tmp_path / "data", {"A": {}})
        yaml_content = "allocation:\n  budget: 100\n  costs:\n    A: 30\n"
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)
        result = allocate(str(config_file), tmp_path / "data")
        assert result["status"] == "Optimal"

    def test_result_keys(self, tmp_path):
        _setup_data_dir(tmp_path, {"A": {}})
        config = {"allocation": {"budget": 100, "costs": {"A": 30}}}
        result = allocate(config, tmp_path)
        expected = {
            "status",
            "selected_initiatives",
            "total_cost",
            "objective_value",
            "total_actual_returns",
            "rule",
            "detail",
        }
        assert set(result.keys()) == expected
