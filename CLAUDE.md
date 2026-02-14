# CLAUDE.md

## Project overview

Portfolio allocation for the impact engine pipeline. Implements pluggable decision-rule
solvers (minimax regret, Bayesian weighted-scenario) using PuLP/CBC, wrapped as a
`PipelineComponent` for the orchestrator.

## Development setup

```bash
pip install -e ".[dev]"
```

## Common commands

- `hatch run test` — run pytest suite
- `hatch run lint` — check with ruff
- `hatch run format` — auto-format with ruff
- `hatch run docs:build` — build Sphinx documentation

## Architecture

- `portfolio_allocation/solver/` — solver package (no orchestrator dependency)
  - `_types.py` — `AllocationSolver` protocol and `SolverResult` TypedDict
  - `_common.py` — shared preprocessing, confidence penalty, result extraction
  - `minimax_regret.py` — minimax regret decision rule (`MinimaxRegretSolver`)
  - `bayesian.py` — weighted-scenario decision rule (`BayesianSolver`)
  - `__init__.py` — public exports and `solve_minimax_regret()` convenience wrapper
- `portfolio_allocation/adapter.py` — orchestrator integration (`AllocateComponent`, `MinimaxRegretAllocate`)
- `portfolio_allocation/tests/` — unit and integration tests
- `docs/source/` — Sphinx docs with executable tutorial notebooks

## Key conventions

- NumPy-style docstrings
- Logging via `logging.getLogger(__name__)` (no print statements)
- Solvers conform to the `AllocationSolver` protocol and return `SolverResult`
- Solver uses internal field names (`id`, `R_best`, `R_med`, `R_worst`); adapter handles mapping
- `_external/` contains reference submodules — do not modify
