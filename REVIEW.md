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

---

## 6. Solver-Agnostic Output Design

With multiple decision theoretic rules planned, the solver output structure becomes
a critical design decision. The current output shape is minimax-regret-specific and
would not generalize cleanly.

### 6.1 Problem: Decision Tangled with Diagnostics

The current `solve_minimax_regret` returns seven keys at the same level:

```python
{
    "status": "Optimal",                        # common
    "selected_initiatives": ["A", "C"],         # common
    "total_cost": 7,                            # common
    "total_actual_returns": {"best": ..., ...}, # common
    "min_max_regret": 3.2,                      # rule-specific
    "v_j_star": {"best": 25, ...},              # rule-specific
    "regrets_for_selected_portfolio": {...},     # rule-specific
}
```

The adapter at `adapter.py:107-108` reads only `status` and `selected_initiatives`,
then goes back to the **original input** at `adapter.py:124-125` to reconstruct
`predicted_returns` and `budget_allocated`. The solver's scenario returns, regrets,
and objective value are computed and discarded.

This structure has two problems:

1. **Adding a new rule means inventing a new result shape.** A maximin solver
   would return `worst_case_return` and `binding_scenario` instead of
   `min_max_regret` and `v_j_star` — different keys at the same level.
   The adapter cannot process these generically.

2. **No way to compare results across rules.** If the pipeline runs both minimax
   regret and maximin on the same input, there is no common field to compare
   objective values or scenario-level outcomes.

### 6.2 Classify Every Output Field

Mapping each field by whether it is common to all rules or specific to one:

| Field | Common | Why |
|-------|--------|-----|
| `status` | Yes | Every solver has a termination status |
| `selected_initiatives` | Yes | Every solver produces a portfolio selection |
| `total_cost` | Yes | Sum of costs — identical logic for all rules |
| `total_actual_returns` | Yes | Per-scenario portfolio returns — same computation regardless of which rule chose the portfolio |
| `min_max_regret` | No | This is the minimax regret objective value |
| `v_j_star` | No | Only regret-based rules need scenario-optimal benchmarks |
| `regrets_for_selected_portfolio` | No | Regret is a minimax regret concept |

### 6.3 What Other Rules Would Add

| Rule | Objective value represents | Rule-specific detail |
|------|--------------------------|---------------------|
| Minimax regret | min max(V_j* − portfolio_j) | v_j_star, regrets per scenario |
| Maximin | max min(portfolio_j) | binding_scenario |
| Hurwicz | max [α·best + (1−α)·worst] | alpha |
| Laplace | max mean(portfolio_j) | — (none) |

Every rule optimizes *something* and may carry rule-specific metadata. The decision
(which initiatives were selected) has identical shape across all rules.

### 6.4 Proposed: `SolverResult` with Core + Detail

Separate the stable common core from the rule-specific diagnostics:

```python
class SolverResult(TypedDict):
    """Common output contract all decision rules must satisfy."""

    status: str                          # solver termination status
    selected_initiatives: list[str]      # IDs of selected initiatives
    total_cost: float                    # aggregate cost of selection
    objective_value: float | None        # what the rule optimized (generic)
    total_actual_returns: dict[str, float]  # per-scenario portfolio returns
    rule: str                            # "minimax_regret", "maximin", etc.
    detail: dict[str, Any]              # rule-specific, opaque to adapter
```

Key design choices:

- **`objective_value`** replaces `min_max_regret`. Every rule optimizes something;
  the generic name lets the adapter log and compare without knowing which rule ran.

- **`rule`** is a string identifier. Downstream code that needs to interpret
  `detail` checks this field first. Without it, a consumer receiving a result dict
  has no way to know what `detail` contains.

- **`detail`** collects all rule-specific diagnostics in a single, contained
  namespace. The adapter does not inspect it — it passes it through.

### 6.5 Concrete Detail Shapes per Rule

```python
# Minimax regret
detail = {
    "v_j_star": {"best": 25.0, "med": 18.0, "worst": 7.0},
    "regrets": {"best": 3.2, "med": 1.1, "worst": 0.0},
}

# Maximin
detail = {
    "binding_scenario": "worst",
}

# Hurwicz
detail = {
    "alpha": 0.6,
}

# Laplace
detail = {}
```

These can be formalized as per-rule `TypedDict` subclasses for type checking, but
the adapter never needs to parse them — it treats `detail` as opaque pass-through.

### 6.6 Result Extraction as Shared Utility

Lines `solver.py:206-217` extract selected initiatives and compute `total_cost`
and `total_actual_returns` from PuLP binary variables. This logic is identical
regardless of decision rule — it is always "iterate over binary variables, collect
those above 0.5, sum costs and returns":

```python
def extract_selection(
    x_vars: dict[str, lp.LpVariable],
    initiatives: list[dict[str, Any]],
    scenarios: list[str],
) -> tuple[list[str], float, dict[str, float]]:
    """Extract selected initiatives and aggregate returns from solved BIP."""
    selected: list[str] = []
    total_cost = 0.0
    total_returns = {s: 0.0 for s in scenarios}
    for i in initiatives:
        if x_vars[i["id"]].varValue > 0.5:
            selected.append(i["id"])
            total_cost += i["cost"]
            for s in scenarios:
                total_returns[s] += i["effective_returns"][s]
    return selected, total_cost, total_returns
```

Each rule calls `extract_selection` after solving its BIP, then packages the
common fields into `SolverResult` and adds its own `detail`. Zero duplication
across rules.

### 6.7 Adapter Pass-Through

The `AllocateResult` contract is owned by the orchestrator — its three fields
(`selected_initiatives`, `predicted_returns`, `budget_allocated`) cannot change.
But the adapter can attach solver output alongside:

```python
result = asdict(AllocateResult(
    selected_initiatives=selected_ids,
    predicted_returns={sid: id_to_initiative[sid]["return_median"] for sid in selected_ids},
    budget_allocated={sid: id_to_initiative[sid]["cost"] for sid in selected_ids},
))
result["solver_detail"] = {
    "rule": solver_result["rule"],
    "objective_value": solver_result["objective_value"],
    "total_actual_returns": solver_result["total_actual_returns"],
    "detail": solver_result["detail"],
}
return result
```

This preserves backward compatibility (the three `AllocateResult` keys are
unchanged) while giving downstream consumers access to:

- **Which rule** was used (`rule`)
- **How well** the portfolio scores (`objective_value`, `total_actual_returns`)
- **Rule-specific diagnostics** (`detail`) for reporting, audit, or rule comparison

Components that only need the allocation decision ignore `solver_detail`.
Components that need to understand *why* this portfolio was chosen — for
reporting, comparison across rules, or audit — read it without coupling to a
specific rule's internals.

### 6.8 Updated Priority Table

With multi-rule support as the driving requirement, the priority order shifts:

| # | Recommendation | Effort | Impact | Section |
|---|---------------|--------|--------|---------|
| 1 | Define `SolverResult` TypedDict with core + detail separation | Low | Critical | 6.4 |
| 2 | Extract shared `extract_selection` utility | Low | High | 6.6 |
| 3 | Accept solver callable via constructor injection in adapter | Low | Critical | 2.2 |
| 4 | Surface `solver_detail` in adapter output | Low | High | 6.7 |
| 5 | Extract shared preprocessing (filter + effective returns) | Low | High | — |
| 6 | Narrow exception handling to PuLP-specific errors | Low | Medium | 2.7 |
| 7 | Expose solver timeout parameter | Low | Medium | 2.8 |
| 8 | Add input validation at adapter boundary | Low | Medium | 2.5 |
| 9 | Make scenario set data-driven | Medium | Medium | 2.1 |
