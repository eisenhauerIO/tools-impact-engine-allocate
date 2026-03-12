"""Tests for job directory reader."""

import json

import pytest

from impact_engine_allocate.job_reader import _extract_estimates, load_initiatives


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_experiment_results():
    return {
        "model_type": "experiment",
        "data": {
            "impact_estimates": {
                "params": {"treatment": 5.0},
                "conf_int": {"treatment": [3.0, 7.0]},
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


class TestExtractEstimates:
    def test_experiment(self):
        result = _extract_estimates(_make_experiment_results())
        assert result["effect_estimate"] == 5.0
        assert result["ci_lower"] == 3.0
        assert result["ci_upper"] == 7.0

    def test_experiment_categorical_key(self):
        data = _make_experiment_results()
        params = data["data"]["impact_estimates"]["params"]
        conf_int = data["data"]["impact_estimates"]["conf_int"]
        pvalues = data["data"]["impact_estimates"]["pvalues"]
        del params["treatment"]
        del conf_int["treatment"]
        del pvalues["treatment"]
        params["treatment[T.True]"] = 4.0
        conf_int["treatment[T.True]"] = [2.0, 6.0]
        pvalues["treatment[T.True]"] = 0.02
        result = _extract_estimates(data)
        assert result["effect_estimate"] == 4.0

    def test_synthetic_control(self):
        data = {
            "model_type": "synthetic_control",
            "data": {
                "impact_estimates": {"att": 10.0, "ci_lower": 8.0, "ci_upper": 12.0},
                "model_summary": {"n_post_periods": 30},
            },
        }
        result = _extract_estimates(data)
        assert result["effect_estimate"] == 10.0
        assert result["ci_lower"] == 8.0
        assert result["ci_upper"] == 12.0

    def test_nearest_neighbour_matching(self):
        data = {
            "model_type": "nearest_neighbour_matching",
            "data": {
                "impact_estimates": {"att": 5.0, "att_se": 1.0},
                "model_summary": {"n_observations": 500},
            },
        }
        result = _extract_estimates(data)
        assert result["effect_estimate"] == 5.0
        assert result["ci_lower"] == pytest.approx(5.0 - 1.96)
        assert result["ci_upper"] == pytest.approx(5.0 + 1.96)

    def test_interrupted_time_series(self):
        data = {
            "model_type": "interrupted_time_series",
            "data": {
                "impact_estimates": {"intervention_effect": 3.5},
                "model_summary": {"n_observations": 200},
            },
        }
        result = _extract_estimates(data)
        assert result["effect_estimate"] == 3.5
        assert result["ci_lower"] == 3.5
        assert result["ci_upper"] == 3.5

    def test_subclassification(self):
        data = {
            "model_type": "subclassification",
            "data": {
                "impact_estimates": {"treatment_effect": 2.0},
                "model_summary": {"n_observations": 300},
            },
        }
        result = _extract_estimates(data)
        assert result["effect_estimate"] == 2.0

    def test_metrics_approximation(self):
        data = {
            "model_type": "metrics_approximation",
            "data": {
                "impact_estimates": {"impact": 7.5},
                "model_summary": {"n_products": 100},
            },
        }
        result = _extract_estimates(data)
        assert result["effect_estimate"] == 7.5

    def test_unknown_model_type_raises(self):
        data = {
            "model_type": "unknown",
            "data": {"impact_estimates": {}, "model_summary": {}},
        }
        with pytest.raises(ValueError, match="Unknown model_type"):
            _extract_estimates(data)


class TestLoadInitiatives:
    def test_loads_from_directories(self, tmp_path):
        costs = {"init_A": 100, "init_B": 200}

        for name, cost in costs.items():
            d = tmp_path / name
            d.mkdir()
            _write_json(d / "impact_results.json", _make_experiment_results())
            _write_json(d / "evaluate_result.json", _make_evaluate_result(0.9))

        result = load_initiatives(tmp_path, costs)
        assert len(result) == 2
        ids = {r["id"] for r in result}
        assert ids == {"init_A", "init_B"}

        for r in result:
            assert r["cost"] == costs[r["id"]]
            assert r["R_med"] == 5.0
            assert r["R_best"] == 7.0
            assert r["R_worst"] == 3.0
            assert r["confidence"] == 0.9

    def test_missing_impact_results_raises(self, tmp_path):
        d = tmp_path / "init_A"
        d.mkdir()
        _write_json(d / "evaluate_result.json", _make_evaluate_result())
        with pytest.raises(FileNotFoundError, match="impact_results.json"):
            load_initiatives(tmp_path, {"init_A": 100})

    def test_missing_evaluate_result_raises(self, tmp_path):
        d = tmp_path / "init_A"
        d.mkdir()
        _write_json(d / "impact_results.json", _make_experiment_results())
        with pytest.raises(FileNotFoundError, match="evaluate_result.json"):
            load_initiatives(tmp_path, {"init_A": 100})

    def test_missing_cost_entry_raises(self, tmp_path):
        d = tmp_path / "init_A"
        d.mkdir()
        _write_json(d / "impact_results.json", _make_experiment_results())
        _write_json(d / "evaluate_result.json", _make_evaluate_result())
        with pytest.raises(ValueError, match="No cost entry"):
            load_initiatives(tmp_path, {})

    def test_skips_non_directories(self, tmp_path):
        (tmp_path / "not_a_dir.txt").write_text("hello")
        d = tmp_path / "init_A"
        d.mkdir()
        _write_json(d / "impact_results.json", _make_experiment_results())
        _write_json(d / "evaluate_result.json", _make_evaluate_result())
        result = load_initiatives(tmp_path, {"init_A": 50})
        assert len(result) == 1
