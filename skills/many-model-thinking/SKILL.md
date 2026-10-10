---
name: many-model-thinking
description: Multi-model thinking and ensemble claim aggregation method pack under Scott Page methodology.
---

# Many-Model Thinking — Scott Page Multi-Model Ensemble

Multi-model decision analysis and ensemble claim aggregation under the Scott Page methodology, integrated into the Capital Decision Lab framework.

## When to Use

- User requests Scott Page multi-model analysis, ensemble thinking, or model diversity evaluations.
- When stress-testing a stock or portfolio thesis across multiple independent mathematical models.
- When running the executable `page` method pack (`capital method run --pack page` or `capital analyze-position --method page`).
- When evaluating committee deliberations with multi-model perspectives (`capital method committee --packs core page thorp`).

## Core Principles

1. **No Heterogeneous Raw Averaging:** Different model families predict different physical/financial quantities. Predictions are converted to structured claim records sharing a `claim_id` before compilation.
2. **Two-Family Minimum:** At least 2 distinct model families must independently support a claim for it to qualify as `robust_positive`. Single-family parameter sweeps are clamped to `conditional`.
3. **Supermajority Rule:** $\text{threshold} = \max(2, \lceil 2A/3 \rceil)$, where $A$ is the count of independent contributing model families / correlation groups.
4. **Heavy-Tail Moment-Safety Veto:** If power-law tail index $\alpha \le 2.0$ (undefined mean) or fit is unavailable, exposure increases are strictly vetoed (`watch` or `hold`).
5. **Deterministic Replay:** All stochastic simulations use local RNG instances with canonical parameter-hash seed derivation. Global random state is never touched.

## Supported Model Families

1. **Continuous Power-Law Tail Diagnostic ([`power_law.md`](references/power_law.md)):**
   Continuous MLE tail exponent $\alpha = 1 + n / \sum \ln(x/x_{\min})$, Kolmogorov-Smirnov distance, and 250-trial parametric bootstrap. Enforces moment existence gates.
2. **Markov Stationary Distribution Diagnostic ([`markov.md`](references/markov.md)):**
   Ergodic transition matrix analysis. Verifies irreducibility via BFS reachability and aperiodicity via BFS spanning tree cycle length GCD before executing uniform-start power iteration.
3. **Bass Diffusion Discrete Model ([`bass.md`](references/bass.md)):**
   Discrete adoption equation $\Delta N(t) = (p + q N(t)/M)(M - N(t))$ with carrying capacity conservation, stagnation checks, and peak adoption detection.
4. **Bernoulli Multi-Armed Bandit Simulation ([`bandits.md`](references/bandits.md)):**
   Stochastic exploration/exploitation simulation supporting `greedy`, `sample_then_greedy`, and `adaptive_epsilon` policies with deterministic RNG draw sequences.

## CLI & Method Pack Usage

```bash
# Run Page method pack on a decision case
capital method run --pack page --case path/to/case.json

# Analyze position with Page method overlay
capital analyze-position --case path/to/case.json --host-inputs path/to/host/ --method page

# Run multi-pack Committee deliberation
capital method committee --packs core page thorp --case path/to/case.json
```

## Detailed References

- [Power-Law Tail Diagnostic Reference](references/power_law.md)
- [Markov Stationary Distribution Reference](references/markov.md)
- [Bass Diffusion Dynamical Reference](references/bass.md)
- [Multi-Armed Bandit Reference](references/bandits.md)
- [Deterministic Claim Compiler Reference](references/claim_compiler.md)
