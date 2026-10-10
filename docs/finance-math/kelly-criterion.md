# Kelly Criterion

Capital Decision Lab treats Kelly as a calculated exposure reference under supplied assumptions, never as an instruction.

For a binary payoff with win probability `p`, loss probability `q`, positive win multiple `g`, and negative loss multiple `l`:

```text
edge = p × g + q × l
full_kelly = -edge / (g × l)
```

The stock-focused layer then applies:

```text
confidence_adjusted = full_kelly × confidence_haircut
fractional_reference = confidence_adjusted × kelly_fraction
capped_exposure = min(max(fractional_reference, 0), user_cap)
```

Negative and zero edge produce zero capped exposure plus a warning atom. Invalid probabilities, payoff signs, fractions, caps, or haircuts produce unavailable atoms. Multi-scenario expected log growth is calculated as `Σ probability × log(1 + exposure × payoff_multiple)` when every logarithm remains in its valid domain.

Kelly is highly sensitive to estimated probabilities and payoff multiples. Outputs therefore retain input references, limitations, and a confidence haircut chosen by the user.

