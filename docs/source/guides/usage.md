# Usage

## Overview

Impact Engine Allocate selects a portfolio of initiatives that maximizes returns
across scenarios while respecting budget and strategic constraints. It reads
initiative data produced by the upstream measure and evaluate stages and applies
a configurable **decision rule** to choose the optimal subset.

The package provides two decision rules. **Minimax regret** selects the
portfolio that minimizes the maximum regret across all scenarios — a
conservative strategy that limits exposure to the worst case. **Bayesian
expected return** maximizes the weighted sum of scenario returns under
user-specified probability weights — useful when the decision-maker has
informative beliefs about scenario likelihoods. Both rules return the same
`RuleResult` dict, making them interchangeable from the orchestrator's
perspective.

---

## End-to-end allocation

The `allocate()` facade loads configuration, reads initiative data from job
directories, preprocesses, and dispatches to the configured decision rule.

```python
from impact_engine_allocate import allocate

result = allocate("allocation_config.yaml", "path/to/pipeline/output")
```

The config file specifies the budget, per-initiative costs, decision rule, and
any rule-specific parameters. See [Configuration](configuration.md) for the
full reference.

---

## Step-by-step usage

For more control, use the lower-level API directly.

### Minimax regret

```python
from impact_engine_allocate import load_config, load_initiatives
from impact_engine_allocate.allocation import MinimaxRegretAllocation, preprocess, empty_rule_result

config = load_config("allocation_config.yaml")
initiatives = load_initiatives("path/to/pipeline/output", config["costs"])

processed = preprocess(initiatives, config["min_confidence_threshold"])
if not processed:
    result = empty_rule_result("No Eligible Initiatives", "minimax_regret")
else:
    solver = MinimaxRegretAllocation()
    result = solver(processed, config["budget"], config["min_portfolio_worst_return"])
```

### Bayesian expected return

```python
from impact_engine_allocate.allocation import BayesianAllocation, preprocess, empty_rule_result

weights = {"best": 0.25, "med": 0.50, "worst": 0.25}

processed = preprocess(initiatives, config["min_confidence_threshold"])
if not processed:
    result = empty_rule_result("No Eligible Initiatives", "bayesian")
else:
    solver = BayesianAllocation(weights=weights)
    result = solver(processed, config["budget"], config["min_portfolio_worst_return"])
```

Weights must be non-negative and sum to 1. Equal weights recover the Laplace
criterion (no scenario preference).

---

## Output contract

Both decision rules return a `RuleResult` dict with the same keys:

| Key | Type | Description |
|-----|------|-------------|
| `status` | `str` | Solver status (`"Optimal"`, `"Infeasible"`, etc.) |
| `selected_initiatives` | `list[str]` | IDs of selected initiatives |
| `total_cost` | `float` | Total cost of selected portfolio |
| `objective_value` | `float` | Objective function value |
| `total_actual_returns` | `dict[str, float]` | Scenario returns for the portfolio |
| `rule` | `str` | Decision rule identifier |
| `detail` | `dict` | Rule-specific diagnostics (see below) |

The `detail` dict carries rule-specific information:

- **Minimax regret**: `v_j_star` (optimal per-scenario returns) and `regrets`
  (per-scenario regret values)
- **Bayesian**: `weights` (the scenario weights used) and `weighted_returns`
  (per-initiative weighted returns for selected initiatives)

---

## Orchestrator integration

Within the full pipeline, the orchestrator wraps `allocate()` in its own
`AllocateComponent` adapter. The adapter lives in the orchestrator repo
(`impact_engine_orchestrator/components/allocate/`), not in this package.

The adapter translates between orchestrator and allocation field names:

| Orchestrator Field | Allocation Field |
|-------------------|--------------|
| `initiative_id` | `id` |
| `return_best` | `R_best` |
| `return_median` | `R_med` |
| `return_worst` | `R_worst` |
| `confidence` | `confidence` (unchanged) |
| `cost` | `cost` (unchanged) |

---

## Pipeline context

The orchestrator pipeline flows through four stages:

```
MEASURE ──► EVALUATE ──► ALLOCATE ──► SCALE
```

The upstream stages write job directories with measurement results and
confidence scores. The allocate stage reads those directories, penalizes
returns by confidence, and selects the optimal portfolio. Low confidence pulls
returns toward worst-case scenarios, making the allocator conservative where
evidence is weak and aggressive where evidence is strong.
