# Impact Engine — Allocate

[![CI](https://github.com/eisenhauerIO/tools-impact-engine-allocate/actions/workflows/ci.yaml/badge.svg)](https://github.com/eisenhauerIO/tools-impact-engine-allocate/actions/workflows/ci.yaml)
[![Docs](https://github.com/eisenhauerIO/tools-impact-engine-allocate/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/eisenhauerIO/tools-impact-engine-allocate/actions/workflows/docs.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/eisenhauerIO/tools-impact-engine-allocate/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Slack](https://img.shields.io/badge/Slack-Join%20Us-4A154B?logo=slack)](https://join.slack.com/t/eisenhauerioworkspace/shared_invite/zt-3lxtc370j-XLdokfTkno54wfhHVxvEfA)

*Portfolio optimization under uncertainty for initiative selection*

Knowing what works is not enough — you must decide where to invest under constraints and uncertainty. Decision theory frames this as a portfolio optimization problem: select the set of initiatives that maximizes returns across scenarios while respecting budget and strategic constraints.

**Impact Engine — Allocate** solves this with two pluggable decision rules. Minimax regret minimizes the maximum regret across all scenarios. A Bayesian solver maximizes expected return under user-specified scenario weights. Both consume confidence-penalized returns — better evidence enables better bets.

## Quick Start

```bash
pip install git+https://github.com/eisenhauerIO/tools-impact-engine-allocate.git
```

```python
from impact_engine_allocate.solver import solve_minimax_regret

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

## Documentation

| Guide | Description |
|-------|-------------|
| [Solver Algorithm](https://eisenhauerio.github.io/tools-impact-engine-allocate/solver/index.html) | Minimax regret formulation and math |
| [Integration](https://eisenhauerio.github.io/tools-impact-engine-allocate/integration/index.html) | Orchestrator integration and field mapping |
| [Tutorial](https://eisenhauerio.github.io/tools-impact-engine-allocate/tutorial/index.html) | Step-by-step walkthrough with notebooks |
| [API Reference](https://eisenhauerio.github.io/tools-impact-engine-allocate/api/index.html) | Auto-generated class and function documentation |

## Development

```bash
hatch run test        # Run tests
hatch run lint        # Run linter
hatch run format      # Format code
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
