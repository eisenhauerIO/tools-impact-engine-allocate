"""Tests for job directory reader."""

import json

import pytest

from impact_engine_allocate.job_reader import load_initiatives


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_measure_result(effect_estimate=5.0, ci_lower=3.0, ci_upper=7.0):
    return {
        "effect_estimate": effect_estimate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": 0.01,
        "sample_size": 1000,
    }


def _make_evaluate_result(confidence=0.85):
    return {
        "initiative_id": "test",
        "confidence": confidence,
        "confidence_range": [0.7, 1.0],
        "strategy": "score",
        "report": "",
    }


class TestLoadInitiatives:
    def test_loads_from_directories(self, tmp_path):
        costs = {"init_A": 100, "init_B": 200}

        for name, cost in costs.items():
            d = tmp_path / name
            d.mkdir()
            _write_json(d / "measure_result.json", _make_measure_result())
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

    def test_missing_measure_result_raises(self, tmp_path):
        d = tmp_path / "init_A"
        d.mkdir()
        _write_json(d / "evaluate_result.json", _make_evaluate_result())
        with pytest.raises(FileNotFoundError, match="measure_result.json"):
            load_initiatives(tmp_path, {"init_A": 100})

    def test_missing_evaluate_result_raises(self, tmp_path):
        d = tmp_path / "init_A"
        d.mkdir()
        _write_json(d / "measure_result.json", _make_measure_result())
        with pytest.raises(FileNotFoundError, match="evaluate_result.json"):
            load_initiatives(tmp_path, {"init_A": 100})

    def test_missing_cost_entry_raises(self, tmp_path):
        d = tmp_path / "init_A"
        d.mkdir()
        _write_json(d / "measure_result.json", _make_measure_result())
        _write_json(d / "evaluate_result.json", _make_evaluate_result())
        with pytest.raises(ValueError, match="No cost entry"):
            load_initiatives(tmp_path, {})

    def test_skips_non_directories(self, tmp_path):
        (tmp_path / "not_a_dir.txt").write_text("hello")
        d = tmp_path / "init_A"
        d.mkdir()
        _write_json(d / "measure_result.json", _make_measure_result())
        _write_json(d / "evaluate_result.json", _make_evaluate_result())
        result = load_initiatives(tmp_path, {"init_A": 50})
        assert len(result) == 1
