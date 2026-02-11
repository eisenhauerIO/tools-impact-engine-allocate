# Portfolio Allocation

Minimax regret portfolio optimization for the impact engine pipeline.

## Overview

This package implements a binary integer linear programming approach to portfolio selection
that minimizes worst-case regret across best, median, and worst-case scenarios. It plugs into
the [impact engine orchestrator](https://github.com/eisenhauerIO/tools-impact-engine-orchestrator)
as the **ALLOCATE** component.

## Key Features

- **Minimax regret optimization** via PuLP/CBC solver
- **Confidence-penalized returns** — low-confidence estimates are pulled toward worst-case
- **Budget and minimum return constraints**
- **Orchestrator integration** via `MinimaxRegretAllocate` pipeline component

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Standalone solver

```python
from portfolio_allocation.solver import solve_minimax_regret

initiatives = [
    {"id": "A", "cost": 4, "R_best": 15, "R_med": 10, "R_worst": 2, "confidence": 0.9},
    {"id": "B", "cost": 3, "R_best": 12, "R_med": 8, "R_worst": 1, "confidence": 0.6},
    {"id": "C", "cost": 3, "R_best": 9, "R_med": 6, "R_worst": 2, "confidence": 0.8},
]

result = solve_minimax_regret(
    initiatives_data=initiatives,
    total_budget=10,
    min_confidence_threshold=0.5,
    min_portfolio_worst_return=0.0,
)
print(result["selected_initiatives"])
```

### As orchestrator component

```python
from portfolio_allocation import MinimaxRegretAllocate

allocator = MinimaxRegretAllocate(
    min_confidence_threshold=0.5,
    min_portfolio_worst_return=4.0,
)

event = {
    "initiatives": [
        {"initiative_id": "A", "cost": 4, "return_best": 15, "return_median": 10, "return_worst": 2, "confidence": 0.9},
        {"initiative_id": "B", "cost": 3, "return_best": 12, "return_median": 8, "return_worst": 1, "confidence": 0.6},
    ],
    "budget": 10,
}

result = allocator.execute(event)
# {"selected_initiatives": [...], "predicted_returns": {...}, "budget_allocated": {...}}
```

## Development

```bash
hatch run test      # Run tests
hatch run lint      # Run linter
hatch run format    # Format code
hatch run docs:build  # Build documentation
```

## Algorithm

The solver uses a three-step approach:

1. **Confidence penalty**: Each initiative's returns are blended toward worst-case based on
   `gamma = 1 - confidence`.
2. **Optimal scenario returns**: For each scenario (best/med/worst), solve an independent
   knapsack to find the maximum achievable return.
3. **Minimax regret**: Select the portfolio minimizing the maximum regret across all scenarios,
   subject to budget and minimum worst-case return constraints.

See `docs/source/solver/` for the full mathematical formulation.
