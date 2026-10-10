# Continuous Power-Law Tail Diagnostic Reference

Grounding: Clauset, Shalizi, and Newman (SIAM Review 2009).

## Mathematical Formulation

For observations $x \ge x_{\min} > 0$:
- **Probability Density Function:** $p(x) = \frac{\alpha - 1}{x_{\min}} \left( \frac{x}{x_{\min}} \right)^{-\alpha}$
- **Cumulative Distribution Function:** $F(x) = 1 - \left( \frac{x}{x_{\min}} \right)^{-(\alpha - 1)}$
- **Continuous Maximum Likelihood Estimator:**
  $$\hat{\alpha} = 1 + \frac{n}{\sum_{i=1}^n \ln(x_i / x_{\min})}$$

## Moment Existence Gates

- **Mean Defined:** $\alpha > 2.0$. If $\alpha \le 2.0$, mean is infinite / undefined (`HEAVY_TAIL_UNDEFINED_MEAN`). Vetoes positive exposure sizing.
- **Variance Defined:** $\alpha > 3.0$. If $2.0 < \alpha \le 3.0$, variance is infinite (`HEAVY_TAIL_INFINITE_VARIANCE_ALLOWED`). Allows binary Kelly sizing while flagging risk.

## Goodness-of-Fit Diagnostic

- **Kolmogorov-Smirnov Distance:**
  $$D = \max_{x \ge x_{\min}} |S(x) - F(x)|$$
- **Parametric Bootstrap:** 250 synthetic datasets generated via inverse CDF transformation $x = x_{\min} (1 - u)^{-1/(\hat{\alpha} - 1)}$ using canonical seed.
- **Hypothesis Test:** If bootstrap $p \ge 0.10$, power-law tail hypothesis is not rejected.
