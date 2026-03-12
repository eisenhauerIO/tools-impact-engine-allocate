# CLAUDE.md

## Project overview

Portfolio allocation for the impact engine pipeline. Implements pluggable decision-rule
solvers (minimax regret, Bayesian weighted-scenario) using PuLP/CBC, with a unified
`allocate()` facade for standalone use and a `PipelineComponent` adapter for the orchestrator.

## Development setup

```bash
pip install hatch
hatch env create
```

## Common commands

- `hatch run test` — run pytest suite
- `hatch run lint` — check with ruff
- `hatch run format` — auto-format with ruff
- `hatch run docs:build` — build Sphinx documentation

## Architecture

- `impact_engine_allocate/models.py` — `AllocateResult` dataclass for pipeline output
- `impact_engine_allocate/config.py` — `AllocationConfig` dataclass + `load_config()` (parse-once pattern)
- `impact_engine_allocate/job_reader.py` — `load_initiatives()` reads pipeline output directories
- `impact_engine_allocate/allocation/` — allocation rules package (no orchestrator dependency)
  - `_types.py` — `AllocationRule` protocol and `RuleResult` TypedDict
  - `_common.py` — shared preprocessing, confidence penalty, result extraction
  - `minimax_regret.py` — minimax regret decision rule (`MinimaxRegretAllocation`)
  - `bayesian.py` — weighted-scenario decision rule (`BayesianAllocation`)
  - `__init__.py` — public exports and `allocate()` facade
- `tests/` — unit and integration tests
- `docs/source/` — Sphinx docs with executable tutorial notebooks

## Verification

1. `hatch run lint` — confirm no ruff errors
2. `hatch run test` — all tests pass
3. `hatch run docs:build` — docs build without warnings

## Key conventions

- NumPy-style docstrings
- Logging via `logging.getLogger(__name__)` (no print statements)
- Rules conform to the `AllocationRule` protocol and return `RuleResult`
- Rules use internal field names (`id`, `R_best`, `R_med`, `R_worst`); adapter handles mapping
- `_external/` contains reference submodules — do not modify
