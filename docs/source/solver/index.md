# Solver Algorithm

## Minimax Regret Formulation

The portfolio allocation solver selects a subset of investment initiatives that **minimizes
the maximum regret** across multiple scenarios. Regret is the difference between the best
achievable return and the actual portfolio return under each scenario.

## Three-Scenario Model

Each initiative provides return estimates under three scenarios:

| Scenario | Field | Description |
|----------|-------|-------------|
| Best | `R_best` | Optimistic outcome |
| Median | `R_med` | Expected outcome |
| Worst | `R_worst` | Pessimistic outcome |

## Confidence Penalty

Initiatives with low confidence have their effective returns penalized:

$$R^{\text{eff}}_{i,j} = (1 - \gamma_i) \cdot R_{i,j} + \gamma_i \cdot R_{i,\text{worst}}$$

where $\gamma_i = 1 - c_i$ and $c_i$ is the confidence score in $[0, 1]$.

- **High confidence** ($c \to 1$): $\gamma \to 0$, returns stay as-is
- **Low confidence** ($c \to 0$): $\gamma \to 1$, all returns collapse to worst-case

## Optimization Steps

### Step 1: Optimal Scenario Returns

For each scenario $j$, solve an independent binary knapsack:

$$V_j^* = \max \sum_i x_i \cdot R^{\text{eff}}_{i,j} \quad \text{s.t.} \quad \sum_i x_i \cdot \text{cost}_i \leq B$$

### Step 2: Minimax Regret

Minimize the maximum regret $\theta$ across all scenarios:

$$\min \theta \quad \text{s.t.} \quad \theta \geq V_j^* - \sum_i x_i \cdot R^{\text{eff}}_{i,j} \quad \forall j$$

Subject to:
- **Budget constraint**: $\sum_i x_i \cdot \text{cost}_i \leq B$
- **Minimum worst return**: $\sum_i x_i \cdot R_{i,\text{worst}} \geq R_{\min}$

## Implementation

The solver uses PuLP with the CBC (COIN-OR Branch and Cut) backend.
Binary decision variables $x_i \in \{0, 1\}$ indicate whether each initiative is selected.
