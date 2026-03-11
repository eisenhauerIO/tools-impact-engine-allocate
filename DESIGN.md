# Design: Portfolio allocation under uncertainty

## Motivation

The evaluate stage of the impact engine pipeline produces scenario-based return estimates
for each initiative. A decision-maker must then select a portfolio — a subset of
initiatives — that performs well across scenarios while respecting a budget constraint.
This is a combinatorial optimization problem under uncertainty, and different decision
rules encode different attitudes toward risk.

## Architecture overview

```
                        ┌─────────────────────────┐
                        │   Caller / Orchestrator  │
                        └────────────┬────────────┘
                                     │ initiatives, budget, params
                                     ▼
                        ┌─────────────────────────┐
                        │      preprocess()       │
                        │  confidence filter +    │
                        │  effective returns      │
                        └────────────┬────────────┘
                                     │ preprocessed initiatives
                          ┌──────────┴──────────┐
                          ▼                     ▼
                ┌──────────────────┐  ┌──────────────────┐
                │ MinimaxRegret    │  │   Bayesian       │
                │ Solver           │  │   Solver         │
                └────────┬─────────┘  └────────┬─────────┘
                         │                     │
                         └──────────┬──────────┘
                                    ▼
                        ┌─────────────────────────┐
                        │      SolverResult       │
                        └─────────────────────────┘
```

All solvers conform to the `AllocationSolver` protocol. Preprocessing is shared via
`_common.py` so that confidence penalties are applied consistently regardless of rule.

## Components

### Solver package (`impact_engine_allocate/solver/`)

| File | Role |
|------|------|
| `_types.py` | `AllocationSolver` protocol and `SolverResult` TypedDict |
| `_common.py` | Shared preprocessing, confidence penalty (`calculate_gamma`), result extraction |
| `minimax_regret.py` | Minimax regret decision rule — minimizes maximum regret across scenarios |
| `bayesian.py` | Bayesian expected-return rule — maximizes weighted sum of scenario returns |
| `__init__.py` | Public exports and `solve_minimax_regret()` convenience wrapper |

### Pipeline integration

| File | Role |
|------|------|
| `models.py` | `AllocateResult` dataclass — typed output for the pipeline stage |

## Data flow

Each initiative enters the solver as a dict with internal field names:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique initiative identifier |
| `cost` | `float` | Cost of the initiative |
| `R_best` | `float` | Return under best-case scenario |
| `R_med` | `float` | Return under median scenario |
| `R_worst` | `float` | Return under worst-case scenario |
| `confidence` | `float` | Evidence confidence score (0–1) |

Preprocessing computes `gamma = 1 - confidence` and blends each scenario return toward
`R_worst` by the penalty factor, producing `effective_returns` per scenario. The solver
then formulates a binary integer program (BIP) over these effective returns using PuLP/CBC.

The output `SolverResult` contains `selected_initiatives`, `total_cost`,
`total_actual_returns` per scenario, and rule-specific `detail`.

## Dependency strategy

PuLP is the only required runtime dependency. It bundles the CBC solver, so no external
solver installation is needed. Optional extras are defined in `pyproject.toml`:

- `dev` — pytest, nbmake, ruff, pre-commit
- `notebooks` — jupyterlab, matplotlib, pandas, numpy

## Future directions

- **Solver facade**: A factory function or facade that selects and runs a solver by name,
  decoupling callers from concrete solver classes.
- **Additional decision rules**: Hurwicz alpha criterion, opportunity-loss rules, or
  multi-objective formulations.
- **Constraint extensions**: Sector caps, dependency constraints between initiatives,
  or minimum selection counts.
