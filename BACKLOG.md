# Portfolio allocation backlog

## Current state

The allocation package provides two decision rules (minimax regret, Bayesian) behind the
`AllocationRule` protocol, a shared preprocessing pipeline, and a unified `allocate()` facade
for standalone use. The adapter has been moved into the orchestrator repo.

- Two pluggable rules behind the `AllocationRule` protocol
- Confidence-penalized effective returns via shared preprocessing
- `allocate(config, data_dir)` facade for standalone use
- `load_config()` + `AllocationConfig` for parse-once config pattern
- `load_initiatives()` job reader for pipeline output directories
- `AllocateResult` dataclass for pipeline output
- Sphinx documentation with executable tutorial notebooks
- CI with ruff linting and pytest

## Phase 0 — Add a public solver interface / facade

**Status**: complete
