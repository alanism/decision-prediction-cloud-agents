# Bayesian Belief Updates

Belief updates use odds form:

```text
prior_odds = prior_probability / (1 - prior_probability)
posterior_odds = prior_odds * likelihood_ratio
posterior_probability = posterior_odds / (1 + posterior_odds)
```

Likelihood ratios are bounded, source quality scales evidence weight, and a maximum probability-change cap limits a single update. A matching thesis sensitivity rule is required. Low-liquidity, low-credibility, noisy, contradictory, or echo-heavy evidence receives less weight.

The result records the prior, likelihood ratio, posterior estimate, confidence, affected assumption, limitations, and projected recalculation paths for Kelly, convexity, and margin safety.
