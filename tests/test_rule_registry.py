"""Tests for the class-based rule registry."""

import pytest

from impact_engine_allocate.allocation._types import (
    RULE_REGISTRY,
    AllocationRule,
    RuleRegistry,
    RuleResult,
)
from impact_engine_allocate.allocation.bayesian import BayesianAllocation
from impact_engine_allocate.allocation.minimax_regret import MinimaxRegretAllocation


def test_built_in_rules_registered():
    assert "minimax_regret" in RULE_REGISTRY.list()
    assert "bayesian" in RULE_REGISTRY.list()


def test_get_class_returns_correct_type():
    assert RULE_REGISTRY.get_class("minimax_regret") is MinimaxRegretAllocation
    assert RULE_REGISTRY.get_class("bayesian") is BayesianAllocation


def test_get_class_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unknown rule"):
        RULE_REGISTRY.get_class("no_such_rule")


def test_list_is_sorted():
    names = RULE_REGISTRY.list()
    assert names == sorted(names)


def test_register_custom_rule():
    """Users can implement AllocationRule and register it."""

    class GreedyAllocation(AllocationRule):
        def __call__(self, initiatives, total_budget, min_portfolio_worst_return) -> RuleResult:
            return {
                "status": "Optimal",
                "selected_initiatives": [],
                "total_cost": 0.0,
                "objective_value": None,
                "total_actual_returns": {},
                "rule": "greedy",
                "detail": {},
            }

    registry = RuleRegistry()
    registry.register("greedy", GreedyAllocation)
    cls = registry.get_class("greedy")
    assert cls is GreedyAllocation
    rule = cls()
    result = rule([], 0.0, 0.0)
    assert result["rule"] == "greedy"


def test_register_non_subclass_raises():
    class NotARule:
        pass

    registry = RuleRegistry()
    with pytest.raises(ValueError, match="must be a subclass"):
        registry.register("bad", NotARule)


def test_separate_registry_instances_are_independent():
    registry_a = RuleRegistry()
    registry_b = RuleRegistry()

    class DummyRule(AllocationRule):
        def __call__(self, initiatives, total_budget, min_portfolio_worst_return) -> RuleResult:
            return {
                "status": "Optimal",
                "selected_initiatives": [],
                "total_cost": 0.0,
                "objective_value": None,
                "total_actual_returns": {},
                "rule": "dummy",
                "detail": {},
            }

    registry_a.register("dummy", DummyRule)
    with pytest.raises(ValueError):
        registry_b.get_class("dummy")
