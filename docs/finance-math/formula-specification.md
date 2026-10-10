# Formula specification

The v1 engines calculate absolute gain/loss, ROI, CAGR, expected value, expected return, population volatility, downside deviation, maximum drawdown, historical value at risk, historical expected shortfall, loss probability, paired correlation, Sharpe, Sortino, Calmar, return-to-drawdown, Kelly, fractional Kelly, and capped fractional Kelly.

All calculations use supplied inputs only and return evidence atoms. Ratios are decimal values rather than percentages. Volatility uses population standard deviation. Drawdown is a positive peak-to-trough magnitude. Historical tail metrics sort supplied periodic returns from lowest upward. Risk-adjusted annualization uses the square root of supplied periods per year.

Invalid domains, zero denominators, insufficient observations, and unsupported inputs produce an unavailable atom with a reason instead of a substitute number.
