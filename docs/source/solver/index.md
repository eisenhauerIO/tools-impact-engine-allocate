# Solver Algorithms

Impact Engine Allocate provides two pluggable decision rules for portfolio selection.
Both share a common preprocessing pipeline (confidence filtering and return
penalization) and return the same `RuleResult` dict.

## Shared Preprocessing

### Three-Scenario Model

Each initiative provides return estimates under three scenarios:

| Scenario | Field | Description |
|----------|-------|-------------|
| Best | `R_best` | Optimistic outcome |
| Median | `R_med` | Expected outcome |
| Worst | `R_worst` | Pessimistic outcome |

### Confidence Penalty

Initiatives with low confidence have their effective returns penalized:

$$R^{\text{eff}}_{i,j} = (1 - \gamma_i) \cdot R_{i,j} + \gamma_i \cdot R_{i,\text{worst}}$$

where $\gamma_i = 1 - c_i$ and $c_i$ is the confidence score in $[0, 1]$.

- **High confidence** ($c \to 1$): $\gamma \to 0$, returns stay as-is
- **Low confidence** ($c \to 0$): $\gamma \to 1$, all returns collapse to worst-case

Both rules operate on the penalized effective returns, so better evidence
enables better bets regardless of which rule is selected.

---

## Minimax Regret

The **minimax regret** rule selects the portfolio that minimizes the maximum
regret across all scenarios. Regret is the difference between the best
achievable return and the actual portfolio return under each scenario.

### Step 1: Optimal Scenario Returns

For each scenario $j$, solve an independent binary knapsack:

$$V_j^* = \max \sum_i x_i \cdot R^{\text{eff}}_{i,j} \quad \text{s.t.} \quad \sum_i x_i \cdot \text{cost}_i \leq B$$

### Step 2: Minimax Regret

Minimize the maximum regret $\theta$ across all scenarios:

$$\min \theta \quad \text{s.t.} \quad \theta \geq V_j^* - \sum_i x_i \cdot R^{\text{eff}}_{i,j} \quad \forall j$$

Subject to:
- **Budget constraint**: $\sum_i x_i \cdot \text{cost}_i \leq B$
- **Minimum worst return**: $\sum_i x_i \cdot R_{i,\text{worst}} \geq R_{\min}$

The `detail` dict returns `v_j_star` (optimal per-scenario returns) and
`regrets` (per-scenario regret values) for inspection.

---

## Bayesian Expected Return

The **Bayesian expected return** rule maximizes the weighted sum of scenario
returns, where weights represent the decision-maker's prior beliefs about
scenario likelihoods.

### Formulation

Given scenario weights $w_j$ (non-negative, summing to 1), the weighted
return for initiative $i$ is:

$$\bar{R}_i = \sum_j w_j \cdot R^{\text{eff}}_{i,j}$$

The solver maximizes the total weighted return:

$$\max \sum_i x_i \cdot \bar{R}_i$$

Subject to:
- **Budget constraint**: $\sum_i x_i \cdot \text{cost}_i \leq B$
- **Minimum worst return**: $\sum_i x_i \cdot R_{i,\text{worst}} \geq R_{\min}$

Equal weights recover the **Laplace criterion** (no scenario preference).
Pessimistic weights (high `worst` weight) produce conservative portfolios
similar to minimax regret.

The `detail` dict returns `weights` (the scenario weights used) and
`weighted_returns` (per-initiative weighted returns for selected initiatives).

---

## Implementation

Both solvers use [PuLP](https://coin-or.github.io/pulp/) with the CBC
(COIN-OR Branch and Cut) backend. Binary decision variables
$x_i \in \{0, 1\}$ indicate whether each initiative is selected.
