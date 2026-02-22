# Impact Engine — Allocate

[![CI](https://github.com/eisenhauerIO/tools-impact-engine-allocate/actions/workflows/ci.yaml/badge.svg)](https://github.com/eisenhauerIO/tools-impact-engine-allocate/actions/workflows/ci.yaml)
[![Docs](https://github.com/eisenhauerIO/tools-impact-engine-allocate/actions/workflows/docs.yaml/badge.svg?branch=main)](https://github.com/eisenhauerIO/tools-impact-engine-allocate/actions/workflows/docs.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/eisenhauerIO/tools-impact-engine-allocate/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Slack](https://img.shields.io/badge/Slack-Join%20Us-4A154B?logo=slack)](https://join.slack.com/t/eisenhauerioworkspace/shared_invite/zt-3lxtc370j-XLdokfTkno54wfhHVxvEfA)

*Portfolio optimization under uncertainty for initiative selection*

Knowing what works is not enough — you must decide where to invest under constraints and uncertainty. Decision theory frames this as a portfolio optimization problem: select the set of initiatives that maximizes returns across scenarios while respecting budget and strategic constraints.

**Impact Engine — Allocate** solves this with two pluggable decision rules. Minimax regret minimizes the maximum regret across all scenarios. A Bayesian solver maximizes expected return under user-specified scenario weights. Both consume confidence-penalized returns — better evidence enables better bets.

[Documentation](https://eisenhauerio.github.io/tools-impact-engine-allocate/)
