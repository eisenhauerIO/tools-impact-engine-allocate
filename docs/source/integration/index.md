# Orchestrator Integration

## Overview

`AllocateComponent` implements the `PipelineComponent` interface from the
impact engine orchestrator. It replaces `MockAllocate` as the **ALLOCATE** stage.

## Field Mapping

The adapter translates between orchestrator and solver field names:

| Orchestrator Field | Solver Field |
|-------------------|--------------|
| `initiative_id` | `id` |
| `return_best` | `R_best` |
| `return_median` | `R_med` |
| `return_worst` | `R_worst` |
| `confidence` | `confidence` (unchanged) |
| `cost` | `cost` (unchanged) |

## Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `solver` | `AllocationSolver` | `MinimaxRegretSolver()` | Decision rule to use |
| `min_confidence_threshold` | `float` | `0.0` | Exclude initiatives below this confidence |
| `min_portfolio_worst_return` | `float` | `0.0` | Minimum aggregate worst-case return |

## Usage

```python
from impact_engine_allocate import AllocateComponent

allocator = AllocateComponent(
    min_confidence_threshold=0.5,
    min_portfolio_worst_return=4.0,
)

# event follows the orchestrator contract
event = {
    "initiatives": [
        {
            "initiative_id": "A",
            "cost": 4,
            "return_best": 15,
            "return_median": 10,
            "return_worst": 2,
            "confidence": 0.9,
        },
    ],
    "budget": 10,
}

result = allocator.execute(event)
# Returns: {"selected_initiatives": [...], "predicted_returns": {...}, "budget_allocated": {...}}
```

To use a different decision rule, inject it via the `solver` parameter:

```python
from impact_engine_allocate import AllocateComponent
from impact_engine_allocate.solver import BayesianSolver

allocator = AllocateComponent(
    solver=BayesianSolver(weights={"best": 0.25, "med": 0.50, "worst": 0.25}),
)
```

## Output Contract

The `execute()` method returns a dict matching `AllocateResult`:

| Field | Type | Description |
|-------|------|-------------|
| `selected_initiatives` | `list[str]` | IDs of selected initiatives |
| `predicted_returns` | `dict[str, float]` | Median return per selected initiative |
| `budget_allocated` | `dict[str, float]` | Cost per selected initiative |
| `solver_detail` | `dict` | Rule identifier, objective value, scenario returns, rule-specific detail |
