# Portfolio allocation backlog

## Current state

The solver package is functional with two decision rules (minimax regret, Bayesian) and
a shared preprocessing pipeline. The adapter has been moved into the orchestrator repo.

- Two pluggable solvers behind the `AllocationSolver` protocol
- Confidence-penalized effective returns via shared preprocessing
- `AllocateResult` dataclass for pipeline output
- Sphinx documentation with executable tutorial notebooks
- CI with ruff linting and pytest

## Phase 0 — Add a public solver interface / facade

**Status**: planned

Right now users must import and instantiate solver classes (`BayesianSolver`,
`MinimaxRegretSolver`) directly. We need a unified entry-point (e.g. a factory
function or facade) that selects and runs the appropriate solver by name, so
callers don't couple to concrete classes.
