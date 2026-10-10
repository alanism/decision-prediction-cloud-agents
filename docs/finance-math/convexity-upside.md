# Convexity and Upside Asymmetry

The convexity engine evaluates supplied bear, base, bull, and optional moonshot scenarios. Scenario values remain modeled assumptions rather than asserted price facts.

Core calculations include:

```text
upside_downside_multiple = bull_payoff / abs(bear_payoff)
breakeven_probability = abs(bear_payoff) / (bull_payoff + abs(bear_payoff))
probability_weighted_upside = Σ probability × positive_payoff
probability_weighted_downside = abs(Σ probability × negative_payoff)
convexity_score = probability_weighted_upside / probability_weighted_downside
```

The engine also reports expected value, expected return, payoff skew, weighted scenario dispersion, downside severity, maximum loss, and tail outcomes. Ratios become unavailable when the required downside is missing or zero. The convexity score is a conservative calculated descriptor, not truth about a security or its future price.

