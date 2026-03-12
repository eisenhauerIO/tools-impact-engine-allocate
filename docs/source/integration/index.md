# Orchestrator Integration

## Overview

The allocate package exposes a functional API (`allocate()`) that the orchestrator wraps
in its own `AllocateComponent` adapter. The adapter lives in the orchestrator repo
(`impact_engine_orchestrator/components/allocate/`), not in this package.

## Field Mapping

The orchestrator adapter translates between orchestrator and allocation field names:

| Orchestrator Field | Allocation Field |
|-------------------|--------------|
| `initiative_id` | `id` |
| `return_best` | `R_best` |
| `return_median` | `R_med` |
| `return_worst` | `R_worst` |
| `confidence` | `confidence` (unchanged) |
| `cost` | `cost` (unchanged) |

## Standalone Usage

```python
from impact_engine_allocate import allocate, load_config, load_initiatives

config = load_config("allocation_config.yaml")
initiatives = load_initiatives("path/to/pipeline/output")
result = allocate(config, initiatives)
```

To use a different decision rule:

```python
from impact_engine_allocate import BayesianAllocation

rule = BayesianAllocation(weights={"best": 0.25, "med": 0.50, "worst": 0.25})
result = rule.solve(initiatives, budget=10)
```

## Output Contract

The `allocate()` function returns a `RuleResult` dict:

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | Solver status |
| `selected_initiatives` | `list[str]` | IDs of selected initiatives |
| `total_cost` | `float` | Total cost of selected portfolio |
| `objective_value` | `float` | Objective function value |
| `total_actual_returns` | `dict[str, float]` | Scenario returns for portfolio |
| `rule` | `str` | Decision rule identifier |
| `detail` | `dict` | Rule-specific detail (scenario returns, regrets, etc.) |
