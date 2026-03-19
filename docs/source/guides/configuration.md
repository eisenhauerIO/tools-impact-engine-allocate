# Configuration

## Overview

Configuration controls the decision rule, budget, costs, and constraint
parameters. Settings can be provided as a YAML file or a Python dict.

---

## YAML configuration

Create a config file and pass the path to `allocate()` or `load_config()`:

```python
from impact_engine_allocate import allocate

result = allocate("allocation_config.yaml", "path/to/pipeline/output")
```

**Minimax regret (default):**

```yaml
allocation:
  budget: 250
  rule: minimax_regret
  min_confidence_threshold: 0.5
  min_portfolio_worst_return: 80
  costs:
    initiative-abc: 100
    initiative-def: 80
    initiative-ghi: 120
```

**Bayesian expected return:**

```yaml
allocation:
  budget: 250
  rule: bayesian
  min_confidence_threshold: 0.5
  min_portfolio_worst_return: 80
  costs:
    initiative-abc: 100
    initiative-def: 80
    initiative-ghi: 120
  weights:
    best: 0.25
    med: 0.50
    worst: 0.25
```

The `weights` key (and any other keys not in the core parameter set) are
forwarded to the decision rule constructor as keyword arguments.

---

## Dict configuration

```python
from impact_engine_allocate import allocate

config = {
    "allocation": {
        "budget": 250,
        "rule": "bayesian",
        "min_confidence_threshold": 0.5,
        "min_portfolio_worst_return": 80,
        "costs": {"initiative-abc": 100, "initiative-def": 80},
        "weights": {"best": 0.25, "med": 0.50, "worst": 0.25},
    }
}

result = allocate(config, "path/to/pipeline/output")
```

---

## Parameter reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `budget` | `float` | *(required)* | Total budget for the portfolio. Must be > 0. |
| `costs` | `dict[str, float]` | *(required)* | Per-initiative cost mapping. Keys are initiative IDs. |
| `rule` | `str` | `"minimax_regret"` | Decision rule: `"minimax_regret"` or `"bayesian"`. |
| `min_confidence_threshold` | `float` | `0.0` | Initiatives below this confidence are excluded. Must be in [0, 1]. |
| `min_portfolio_worst_return` | `float` | `0.0` | Minimum aggregate worst-case return for the selected portfolio. |

Additional keys are forwarded as keyword arguments to the decision rule
constructor. For the Bayesian rule, this means `weights`.

---

## Solver-specific parameters

### Bayesian rule

| Parameter | Type | Description |
|-----------|------|-------------|
| `weights` | `dict[str, float]` | Scenario probability weights. Keys must be `best`, `med`, `worst`. Must be non-negative and sum to 1. |

Equal weights (`{"best": 0.33, "med": 0.34, "worst": 0.33}`) recover the
Laplace criterion.

### Minimax regret rule

The minimax regret rule takes no additional parameters.

---

## Validation

`load_config()` validates all parameters on load and raises `ValueError` for
any violations:

- `budget` must be > 0
- `rule` must be `"minimax_regret"` or `"bayesian"`
- `min_confidence_threshold` must be in [0, 1]
- `costs` must be a non-empty dict

After validation, the returned dict is fully trusted — no downstream code
re-validates.
