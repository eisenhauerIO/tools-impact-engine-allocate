# Architecture Review: Extensibility and Modularity

## Executive Summary

The `portfolio-allocation` package demonstrates strong architectural foundations —
clean separation between solver and adapter, immutable data flow, and a well-defined
integration contract. However, several structural decisions limit extensibility for
future growth. This review identifies what works well and where targeted changes
would improve the package's ability to accommodate new solvers, scenarios, constraints,
and output consumers without requiring deep modifications to existing code.

---

## 1. What Works Well

### 1.1 Solver / Adapter Separation

The two-module architecture (`solver.py` for pure optimization, `adapter.py` for
orchestrator integration) is the package's strongest design decision. It delivers
three concrete benefits:

- **Independent testability**: solver functions can be tested with plain dicts and
  no orchestrator dependency (`test_solver.py:84-166`).
- **Standalone usage**: researchers can call `solve_minimax_regret()` directly
  without the pipeline framework.
- **Decoupled naming**: the solver uses compact internal names (`R_best`, `R_med`,
  `R_worst`) while the adapter maps to orchestrator conventions — neither module
  needs to know the other's vocabulary.

### 1.2 Immutable Data Flow

`calculate_effective_returns` creates new dicts via `{**initiative, ...}` rather
than mutating input (`solver.py:79`). Tests explicitly verify this
(`test_solver.py:43-52`). This makes the solver composable and safe for
higher-level code to reuse input across multiple solver invocations.

### 1.3 Confidence Penalty Injection

The `confidence_penalty_func` parameter on both `calculate_effective_returns` and
`solve_minimax_regret` (`solver.py:45`, `solver.py:132`) is a well-placed extension
point. It allows callers to substitute alternative penalty models (e.g., quadratic
decay, threshold cutoff) without modifying solver internals. The test suite
validates this explicitly (`test_solver.py:76-81`).

### 1.4 Graceful Orchestrator Decoupling

The try/except import fallback in `adapter.py:11-30` means the package installs
and runs with `pulp` as its only runtime dependency. This is the correct pattern
for a pipeline component that needs to be testable in isolation.

### 1.5 Determinism Guarantees

Both test modules verify that identical inputs produce identical outputs
(`test_solver.py:99-104`, `test_adapter.py:37-42`). This is important for
reproducibility in audit-sensitive allocation workflows and is easy to overlook.

---

## 2. Extensibility Concerns

### 2.1 Hardcoded Scenario Set

**Location**: `solver.py:17`

```python
SCENARIOS = ["best", "med", "worst"]
```

Every function in the solver iterates over this module-level constant. The field
mapping in `calculate_effective_returns` (`solver.py:70-74`) hard-maps scenario
names to specific dict keys:

```python
r_base_map = {
    "best": initiative["R_best"],
    "med": initiative["R_med"],
    "worst": initiative["R_worst"],
}
```

**Impact**: Adding a new scenario (e.g., "catastrophic", "expected") requires
changes in `solver.py` (the constant, the mapping, and the BIP formulation),
`adapter.py` (field mapping), and all test fixtures. The scenario set should be
derivable from the data rather than hard-coded.

**Recommendation**: Define scenarios as a data-driven mapping, e.g., a list of
`(scenario_name, field_key)` pairs, and pass it through the solver functions. The
current three-scenario model remains the default, but the structure would allow
extension without modifying solver internals.

### 2.2 No Solver Abstraction / Strategy Interface

The adapter directly calls `solve_minimax_regret` (`adapter.py:100`). There is no
abstraction boundary between "the adapter needs an allocation solver" and "the
solver is specifically minimax regret."

**Impact**: If the pipeline needs to support alternative solvers (e.g., mean-variance,
CVaR, max-min return), each would either need its own adapter or the existing adapter
would accumulate conditional logic to select between solvers.

**Recommendation**: Introduce a lightweight solver protocol (a callable or ABC)
that `MinimaxRegretAllocate` accepts via constructor injection. The current
`solve_minimax_regret` function already conforms to such a protocol — it accepts
initiatives, budget, and thresholds and returns a result dict. Making this explicit
would allow the adapter to remain stable while solvers vary:

```python
class MinimaxRegretAllocate(PipelineComponent):
    def __init__(self, solver_func=solve_minimax_regret, ...):
        self._solver = solver_func
```

### 2.3 Untyped Dict Contracts

All data flows through `dict[str, Any]` — initiatives, solver results, and adapter
results. The only structured type is the `AllocateResult` dataclass
(`adapter.py:24-30`), which is itself immediately decomposed to a dict via `asdict`
(`adapter.py:127`).

**Impact**: There is no compile-time or runtime enforcement that an initiative dict
contains the required keys (`id`, `cost`, `R_best`, `R_med`, `R_worst`,
`confidence`). A missing or misspelled key produces a `KeyError` deep in the solver
rather than a clear validation error at the boundary. This makes the code harder to
extend because developers must read implementation to discover the expected shape.

**Recommendation**: Define `TypedDict` classes (or dataclasses) for:
- Solver input initiative
- Solver result
- Adapter input event

These can coexist with the current dict-based flow (TypedDict is structural, not
nominal) while giving editors, linters, and future developers a machine-readable
contract.

### 2.4 Adapter Returns Only Median Returns

**Location**: `adapter.py:124`

```python
predicted_returns={sid: id_to_initiative[sid]["return_median"] for sid in selected_ids},
```

The `AllocateResult.predicted_returns` field maps each selected initiative to its
`return_median` value. The solver actually computes effective returns across all
three scenarios, confidence-adjusted regrets, and v_j_star values — none of which
surface in the adapter output.

**Impact**: Downstream pipeline components that need scenario-level returns,
regret values, or the solver's optimization metadata must either re-run the solver
or bypass the adapter entirely. The adapter currently discards the richest part of
the solver's output.

**Recommendation**: Either extend `AllocateResult` to carry optional scenario-level
data, or store the full `solver_result` dict under an additional key (e.g.,
`"solver_detail"`) so downstream consumers can access it without coupling to the
solver directly.

### 2.5 No Input Validation at the Boundary

Neither the solver nor the adapter validates inputs before processing:

- `solver.py`: no check that initiative dicts contain required keys, that costs
  and returns are numeric, or that budget is non-negative.
- `adapter.py:94-95`: directly indexes into `event["initiatives"]` and
  `event["budget"]` with no defensive checks.

`calculate_gamma` validates its own input (`solver.py:38-39`), but this is the
only validation in the package.

**Impact**: Invalid input produces opaque errors (`KeyError`, PuLP exceptions)
rather than actionable messages. This is acceptable for internal-only code but
becomes a problem as the number of callers grows.

**Recommendation**: Add a thin validation layer at the adapter boundary
(`execute()` entry point) that checks for required keys and basic type/range
invariants. Keep the solver free of validation — it's internal code that
should trust its caller.

### 2.6 Field Mapping Is One-Directional and Non-Configurable

**Location**: `adapter.py:33-38`

```python
_FIELD_MAP_IN: dict[str, str] = {
    "initiative_id": "id",
    "return_best": "R_best",
    "return_median": "R_med",
    "return_worst": "R_worst",
}
```

The mapping only goes orchestrator → solver. The reverse mapping (solver → orchestrator)
for the output is done implicitly: the adapter uses `id_to_initiative` to look up
original field values by initiative ID (`adapter.py:98`, `adapter.py:124-125`).

**Impact**: If the orchestrator's field names change, or if a different upstream
system uses different names, the mapping must be changed in the source code. There
is no way to configure it at runtime.

**Recommendation**: Accept an optional `field_map` parameter in the
`MinimaxRegretAllocate` constructor, defaulting to the current `_FIELD_MAP_IN`.
This makes the adapter reusable across different upstream schemas without
subclassing.

### 2.7 Broad Exception Handling in Solver

**Location**: `solver.py:114`, `solver.py:198`

```python
except Exception:
    logger.exception("Error solving for scenario %s", scenario_name)
```

Both PuLP `.solve()` calls catch bare `Exception`. This swallows unexpected errors
(e.g., `MemoryError`, `KeyboardInterrupt` via nested exception chains) alongside
expected solver failures.

**Impact**: In production, a genuine bug could be silently converted to an
"Error" status return, making debugging difficult.

**Recommendation**: Catch `pulp.PulpSolverError` (or the specific PuLP exception
hierarchy) rather than bare `Exception`. Let unexpected errors propagate.

### 2.8 No Solver Timeout Configuration

PuLP's CBC solver is invoked with `msg=False` but no time limit
(`solver.py:113`, `solver.py:197`):

```python
prob.solve(lp.PULP_CBC_CMD(msg=False))
```

**Impact**: For large initiative sets, CBC can run for an unbounded amount of time.
In a pipeline context, a single slow solver call can block the entire workflow.

**Recommendation**: Expose a `solver_timeout` parameter (passed to
`PULP_CBC_CMD(timeLimit=...)`) with a sensible default (e.g., 60 seconds). This
is a one-line change in the solver and a constructor parameter in the adapter.

---

## 3. Modularity Assessment

### 3.1 Package Public Surface

The `__init__.py` exports exactly two names:

```python
__all__ = ["MinimaxRegretAllocate", "solve_minimax_regret"]
```

This is appropriate. The intermediate functions (`calculate_gamma`,
`calculate_effective_returns`, `calculate_optimal_scenario_returns`) are accessible
via `portfolio_allocation.solver` but not promoted to top-level exports. Users who
need them can import explicitly; users who don't are not distracted.

The internal helper `_to_solver_format` is correctly prefixed with underscore.

### 3.2 Module Dependency Graph

```
__init__.py
  ├── adapter.py
  │     └── solver.py
  └── solver.py
```

The dependency graph is a clean DAG with no cycles. `solver.py` has zero internal
imports — it depends only on `pulp`, `logging`, `math`, and stdlib `typing`.
`adapter.py` depends on `solver.py` and optionally on the orchestrator. This is
the correct layering.

### 3.3 Test Organization

Tests are co-located inside the package (`portfolio_allocation/tests/`) rather than
in a top-level `tests/` directory. This is fine for a single-package project but
means `portfolio_allocation/tests/` ships in the wheel unless explicitly excluded.

**Observation**: `pyproject.toml` does not exclude the tests directory from the
wheel build:

```toml
[tool.hatch.build.targets.wheel]
packages = ["portfolio_allocation"]
```

This includes `portfolio_allocation/tests/` in the distributed package. For a
pipeline-internal package this is low-risk, but for a published package the tests
and fixtures should be excluded from the wheel.

### 3.4 Single-File Solver Scalability

At 231 lines, `solver.py` is manageable. However, it contains four public functions
serving three distinct responsibilities:

1. Confidence penalty calculation (`calculate_gamma`)
2. Effective return computation (`calculate_effective_returns`)
3. Scenario-optimal return computation (`calculate_optimal_scenario_returns`)
4. Main minimax regret solver (`solve_minimax_regret`)

If the package grows to support additional solvers or constraint types, splitting
the solver module along these responsibilities (e.g., `penalties.py`,
`knapsack.py`, `minimax.py`) would improve navigability. At current size this is
not necessary.

---

## 4. Prioritized Recommendations

Ordered by impact-to-effort ratio:

| # | Recommendation | Effort | Impact | Section |
|---|---------------|--------|--------|---------|
| 1 | Add `TypedDict` definitions for initiative and result shapes | Low | High | 2.3 |
| 2 | Expose solver timeout parameter | Low | High | 2.8 |
| 3 | Narrow exception handling to PuLP-specific errors | Low | Medium | 2.7 |
| 4 | Add input validation at adapter boundary | Low | Medium | 2.5 |
| 5 | Surface solver detail in adapter output | Low | Medium | 2.4 |
| 6 | Accept solver callable via constructor injection | Low | Medium | 2.2 |
| 7 | Make field mapping configurable | Low | Low | 2.6 |
| 8 | Make scenario set data-driven | Medium | Medium | 2.1 |
| 9 | Exclude tests from wheel build | Low | Low | 3.3 |

---

## 5. Conclusion

The package is well-structured for its current scope: a single minimax regret solver
serving one pipeline stage. The solver/adapter split, immutable data flow, and
fallback import pattern are solid foundations.

The primary extensibility gaps are:

1. **Rigidity in the scenario model** — hardcoded three-scenario set limits future
   flexibility.
2. **No solver abstraction** — the adapter is tightly coupled to a single solver
   function.
3. **Untyped boundaries** — dict-based contracts lack machine-readable structure.
4. **Information loss at the adapter** — rich solver output is reduced to median
   returns only.

None of these require immediate action — the package works correctly for its current
use case. But addressing items 1-6 in the priority table above would position the
package well for growth into a multi-solver, multi-scenario allocation framework.
