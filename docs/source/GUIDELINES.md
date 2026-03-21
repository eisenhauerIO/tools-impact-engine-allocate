# Documentation Guidelines — Allocate

Ecosystem-wide conventions: see `docs/GUIDELINES.md` at the workspace root.
This file documents conventions specific to the allocate component.

---

## Page map

| Page | Purpose |
|------|---------|
| `README.md` | Package positioning and quick start. Also the docs landing page. |
| `guides/usage.md` | End-to-end usage: both decision rules (Minimax Regret and Bayesian). |
| `guides/configuration.md` | Full parameter reference: budget, costs, rule, thresholds, solver parameters. |
| `solver/index.md` | Mathematical exposition of the optimisation problem and decision rules. |
| `api/index.md` | Auto-generated from source. Do not hand-edit. |
| `tutorial/Tutorial.ipynb` | End-to-end portfolio allocation walkthrough. |
| `tutorial/Visualization.ipynb` | Visualising allocation results and regret surfaces. |

---

## Sidebar structure

```
Guides     → usage, configuration, solver, api
Tutorials  → Tutorial, Visualization
```

---

## Naming conventions

- Public API field names use full snake_case: `return_best`, `return_median`, `return_worst`.
- Internal solver field names (`R_best`, `R_med`, `R_worst`) must never appear in user-facing docs.
- Decision rule names: `minimax_regret` and `bayesian` (lowercase, as passed in config).

---

## Tutorials

All tutorial notebooks are executable — no external API keys required.
