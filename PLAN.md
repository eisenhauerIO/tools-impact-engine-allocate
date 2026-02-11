# Modernize portfolio-allocation to impact-engine standards

## Context

The portfolio-allocation project is a prototype minimax regret solver living as flat scripts (`support.py` + notebooks). It needs to become a proper Python package matching the tools-impact-engine ecosystem conventions so it can plug into the orchestrator as the real ALLOCATE component (replacing `MockAllocate`).

The solver algorithm itself is sound and does not change. All work is structural, quality, and integration. Changes are confined to this package only — `_external/` is untouched.

## Current status

| Step | Description | Status |
|------|-------------|--------|
| 1 | Scaffolding: `pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml` | DONE |
| 2 | `portfolio_allocation/solver.py` from `support.py` | DONE |
| 3 | `portfolio_allocation/adapter.py` (PipelineComponent) | DONE |
| 4 | `portfolio_allocation/__init__.py` | DONE |
| 5 | Tests (`test_solver.py`, `test_adapter.py`) | DONE |
| 6 | Sphinx documentation setup | DONE |
| 7 | Update and move notebooks to `docs/source/tutorial/` | DONE |
| 8 | GitHub Actions CI workflows | DONE |
| 9 | Cleanup and project docs (README, CLAUDE.md, .envrc, delete old files) | DONE |
| 10 | Lint, verify, and ship (push to GitHub, confirm all gates pass) | DONE |

## Target structure

```
portfolio-allocation/
├── pyproject.toml                    # NEW (replaces environment.yaml)
├── .pre-commit-config.yaml           # NEW
├── .gitignore                        # NEW
├── .envrc                            # UPDATE (conda -> hatch)
├── .github/
│   └── workflows/
│       ├── ci.yaml                   # NEW (lint + test)
│       └── docs.yaml                 # NEW (build + deploy docs)
├── CLAUDE.md                         # NEW
├── README.md                         # REPLACE (expand Readme.md)
├── _external/                        # UNCHANGED
├── portfolio_allocation/             # NEW package
│   ├── __init__.py
│   ├── solver.py                     # FROM support.py (modernized)
│   ├── adapter.py                    # NEW (PipelineComponent wrapper)
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_solver.py
│       └── test_adapter.py
├── docs/
│   └── source/
│       ├── conf.py                   # NEW Sphinx config
│       ├── index.md                  # Landing page (includes README)
│       ├── _static/                  # Diagrams, custom CSS
│       ├── _templates/
│       ├── solver/
│       │   └── index.md              # Algorithm explanation
│       ├── integration/
│       │   └── index.md              # Orchestrator integration guide
│       ├── api/
│       │   └── index.md              # Auto-generated API reference
│       └── tutorial/
│           ├── index.md
│           ├── Tutorial.ipynb        # MOVE from root (walkthrough)
│           └── Visualization.ipynb   # MOVE from root (results analysis)
```

**Deleted**: `support.py`, `run_all.py`, `environment.yaml`, `regression_test.obj`, `Readme.md`

## Implementation details

### 1. Scaffolding — `pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`

**`pyproject.toml`** matching orchestrator conventions:
- hatchling build backend, `requires-python = ">=3.10"`
- Runtime dep: `pulp` only
- Optional deps: `dev` (pytest, ruff, pre-commit), `notebooks` (jupyterlab, matplotlib, pandas, numpy)
- Ruff config: `select = ["D", "E", "F", "I"]`, `convention = "numpy"`, `line-length = 120`, `extend-exclude = ["_external", "docs/build"]`
- pytest: `testpaths = ["portfolio_allocation/tests"]`
- Hatch scripts: `test`, `lint`, `format`
- Hatch `docs` environment (separate from default, following orchestrator pattern):
  ```toml
  [tool.hatch.envs.docs]
  dependencies = ["sphinx>=7.0", "sphinx-rtd-theme", "myst-parser", "nbsphinx", "pypandoc", "ipykernel", "nbconvert"]

  [tool.hatch.envs.docs.scripts]
  build = "sphinx-build -b html docs/source docs/build/html"
  ```

**`.pre-commit-config.yaml`** matching both reference projects' hooks:
- `nbstripout` (rev 0.8.1) — strip notebook outputs
- `pre-commit-hooks` (rev v5.0.0):
  - `check-added-large-files` (--maxkb=500)
  - `check-merge-conflict`
  - `check-yaml`
  - `end-of-file-fixer`
  - `trailing-whitespace`
- `ruff-pre-commit` (rev v0.8.4):
  - `ruff --fix` on python + jupyter
  - `ruff-format` on python + jupyter
- Local hooks:
  - `pytest` — runs `hatch run test`, always_run (matching measure project)
  - `execute-notebooks` — runs tutorial notebooks via nbconvert to verify they execute cleanly

After scaffolding: `pre-commit install` to activate hooks

### 2. Create `portfolio_allocation/solver.py` from `support.py`

Modernize without changing algorithm:
- **Type hints** on all functions (`float`, `list[dict[str, Any]]`, `Callable[[float], float]`, etc.)
- **NumPy-style docstrings** on all public functions
- **Logging** via `logging.getLogger(__name__)` — replace all `print()` calls
- **No input mutation** — `calculate_effective_returns` returns new dicts via `{**initiative, ...}` instead of mutating
- **Rename** `solve_minimax_regret_optimization` → `solve_minimax_regret`
- **Keep internal field names** (`R_best`, `R_med`, `R_worst`, `id`) — mapping happens in adapter

### 3. Create `portfolio_allocation/adapter.py` — PipelineComponent

The critical integration piece. Wraps solver for orchestrator use.

- Implements `PipelineComponent.execute(event: dict) -> dict`
- **try/except import** for orchestrator classes (fallback ABCs when orchestrator not installed)
- **Field mapping** in adapter layer:
  - `initiative_id` ↔ `id`, `return_best` ↔ `R_best`, `return_median` ↔ `R_med`, `return_worst` ↔ `R_worst`
  - `confidence` and `cost` unchanged
- **Constructor params**: `min_confidence_threshold` and `min_portfolio_worst_return` (defaults 0.0 = no constraint)
- Returns `asdict(AllocateResult(...))` matching contract: `selected_initiatives`, `predicted_returns`, `budget_allocated`

### 4. Create `portfolio_allocation/__init__.py`

Export public API: `MinimaxRegretAllocate`, `solve_minimax_regret`

### 5. Create tests

**`test_solver.py`** — unit tests:
- `calculate_gamma`: boundary values, out-of-range error
- `calculate_effective_returns`: no mutation, correctness at confidence extremes
- `solve_minimax_regret`: optimal status, budget constraint, confidence filtering, determinism, edge cases (single initiative, zero budget, all same confidence)

**`test_adapter.py`** — integration tests (matching orchestrator patterns):
- Contract invariants: result keys, selected subset of input, budget respected
- Determinism: repeated calls produce identical output
- Edge cases: budget too small, single initiative, all filtered by confidence
- Field mapping: roundtrip ID preservation

### 6. Set up Sphinx documentation

Following the orchestrator's docs pattern (`docs/source/` layout, separate hatch `docs` env, `hatch run docs:build`).

**`docs/source/conf.py`** — Sphinx config matching orchestrator:
- Extensions: `sphinx.ext.autodoc`, `sphinx.ext.napoleon`, `sphinx.ext.mathjax`, `myst_parser`, `nbsphinx`
- Theme: `sphinx_rtd_theme`
- `nbsphinx_execute = "always"`, `nbsphinx_allow_errors = False`
- `sys.path` insert for `portfolio_allocation` package
- Source suffixes: `.md` and `.rst`

**`docs/source/index.md`** — Landing page:
- Include `../../README.md` via myst `include` directive
- Toctree sections: solver, integration, tutorial, api

**`docs/source/solver/index.md`** — Algorithm documentation:
- Minimax regret formulation explanation
- Three-scenario model (best/med/worst)
- Confidence penalty mechanism
- Budget and minimum return constraints

**`docs/source/integration/index.md`** — Orchestrator integration guide:
- How `MinimaxRegretAllocate` fits the ALLOCATE stage
- Field mapping table (orchestrator ↔ solver)
- Constructor parameters and defaults
- Usage example with orchestrator

**`docs/source/api/index.md`** — API reference:
- Autodoc for `portfolio_allocation.solver` (public functions)
- Autodoc for `portfolio_allocation.adapter` (MinimaxRegretAllocate)

**`docs/source/tutorial/`** — Both notebooks live here as the single source of truth for all documentation. Executed by nbsphinx during build.
- `Tutorial.ipynb` — step-by-step walkthrough
- `Visualization.ipynb` — results analysis and plots

### 7. Update notebooks

- `from support import ...` → `from portfolio_allocation.solver import ...`
- `solve_minimax_regret_optimization` → `solve_minimax_regret`
- Remove pickle-based regression test cells from Tutorial.ipynb
- Both notebooks move to `docs/source/tutorial/`

### 8. GitHub Actions CI

Following orchestrator patterns (`.github/workflows/ci.yaml` and `docs.yaml`).

**`.github/workflows/ci.yaml`** — lint + test on push/PR to main:
- Python matrix: 3.10, 3.11, 3.12
- Steps: checkout, install hatch, `hatch run lint`, `hatch run test`

**`.github/workflows/docs.yaml`** — build + deploy docs on push/PR to main:
- Steps: checkout, install hatch + pandoc, `hatch run docs:build`
- Deploy to GitHub Pages on main branch push

### 9. Cleanup and project docs

- Delete: `support.py`, `run_all.py`, `environment.yaml`, `regression_test.obj`, `Readme.md`
- Create: `README.md` (expanded), `CLAUDE.md` (dev workflow + design philosophy), `.envrc` (hatch-based)

### 10. Lint, verify, and ship

- `hatch run format` + `hatch run lint` — fix any issues
- `hatch run test` — all tests pass
- `hatch run docs:build` — docs build without errors
- Commit all changes and push to GitHub
- Confirm tests pass, lint is clean, and docs build succeeds after push

## Key files to modify/reference

| File | Role |
|------|------|
| `support.py` | Source of solver logic → becomes `solver.py` |
| `_external/tools-impact-engine-orchestrator/.../allocate/mock.py` | Reference adapter pattern to follow |
| `_external/tools-impact-engine-orchestrator/.../contracts/allocate.py` | AllocateResult contract to satisfy |
| `_external/tools-impact-engine-orchestrator/.../contracts/evaluate.py` | Input field names (initiative_id, return_best, etc.) |
| `_external/tools-impact-engine-orchestrator/pyproject.toml` | Reference for ruff/hatch/pytest config |
| `_external/tools-impact-engine-orchestrator/docs/source/conf.py` | Reference Sphinx config |

## Verification

1. `hatch run test` — all solver and adapter tests pass
2. `hatch run lint` — no ruff violations
3. `hatch run docs:build` — Sphinx builds cleanly (including notebook execution)
4. Integration: instantiate `MinimaxRegretAllocate` and call `execute()` with orchestrator-shaped input, verify AllocateResult contract
5. Commit and `git push` to GitHub
6. Confirm all three gates pass post-push: tests green, lint clean, docs build clean
