# CLAUDE.md

## Project overview

Portfolio allocation for the impact engine pipeline. Implements minimax regret portfolio
optimization using PuLP/CBC, wrapped as a `PipelineComponent` for the orchestrator.

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

- `portfolio_allocation/solver.py` — core optimization (pure functions, no orchestrator dependency)
- `portfolio_allocation/adapter.py` — orchestrator integration (`MinimaxRegretAllocate`)
- `portfolio_allocation/tests/` — unit and integration tests
- `docs/source/` — Sphinx docs with executable tutorial notebooks

## Key conventions

- NumPy-style docstrings
- Logging via `logging.getLogger(__name__)` (no print statements)
- Solver uses internal field names (`id`, `R_best`, `R_med`, `R_worst`); adapter handles mapping
- `_external/` contains reference submodules — do not modify
