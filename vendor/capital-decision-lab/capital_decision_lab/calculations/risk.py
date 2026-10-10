"""Historical risk and risk-adjusted calculations."""

from __future__ import annotations

import math
import statistics
from typing import Any

from capital_decision_lab.contracts.validation import unavailable_result


def _atom(value: float, formula: str, *, unit: str = "ratio", refs: list[str] | None = None) -> dict:
    return {
        "value": value,
        "provenance_class": "calculated",
        "unit": unit,
        "input_refs": refs or ["periodic_returns"],
        "formula_ref": formula,
        "limitations": ["Historical calculation from supplied observations"],
    }


def _numbers(values: Any, minimum: int) -> tuple[list[float] | None, str | None]:
    if not isinstance(values, list) or len(values) < minimum:
        return None, f"at least {minimum} observations are required"
    if any(
        not isinstance(item, (int, float))
        or isinstance(item, bool)
        or not math.isfinite(float(item))
        for item in values
    ):
        return None, "observations must be finite numbers"
    return [float(item) for item in values], None


def volatility(observations: list[float]) -> dict:
    values, reason = _numbers(observations, 2)
    if reason:
        return unavailable_result(reason, unit="ratio", input_refs=["periodic_returns"])
    return _atom(statistics.pstdev(values), "risk.volatility.v1")


def downside_deviation(observations: list[float], *, target: float = 0.0) -> dict:
    values, reason = _numbers(observations, 1)
    if reason or not isinstance(target, (int, float)) or not math.isfinite(float(target)):
        return unavailable_result(reason or "target must be finite", unit="ratio", input_refs=["periodic_returns", "target"])
    downside = [min(value - float(target), 0.0) ** 2 for value in values]
    return _atom(
        math.sqrt(sum(downside) / len(downside)),
        "risk.downside_deviation.v1",
        refs=["periodic_returns", "target"],
    )


def maximum_drawdown(levels: list[float]) -> dict:
    values, reason = _numbers(levels, 1)
    if reason:
        return unavailable_result(reason, unit="ratio", input_refs=["value_series"])
    if any(value <= 0 for value in values):
        return unavailable_result("value series must be positive", unit="ratio", input_refs=["value_series"])
    peak = values[0]
    maximum = 0.0
    for value in values:
        peak = max(peak, value)
        maximum = max(maximum, (peak - value) / peak)
    return _atom(maximum, "risk.maximum_drawdown.v1", refs=["value_series"])


def loss_probability(observations: list[float]) -> dict:
    values, reason = _numbers(observations, 1)
    if reason:
        return unavailable_result(reason, unit="probability", input_refs=["periodic_returns"])
    return _atom(
        sum(value < 0 for value in values) / len(values),
        "risk.loss_probability.v1",
        unit="probability",
    )


def _tail(observations: list[float], confidence: float) -> tuple[list[float] | None, str | None]:
    values, reason = _numbers(observations, 1)
    if reason:
        return None, reason
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 < confidence < 1:
        return None, "confidence must be between zero and one"
    count = max(1, math.ceil((1.0 - float(confidence)) * len(values)))
    return sorted(values)[:count], None


def value_at_risk(observations: list[float], *, confidence: float = 0.95) -> dict:
    tail, reason = _tail(observations, confidence)
    if reason:
        return unavailable_result(reason, unit="ratio", input_refs=["periodic_returns", "confidence"])
    return _atom(
        max(0.0, -tail[-1]),
        "risk.value_at_risk.v1",
        refs=["periodic_returns", "confidence"],
    )


def expected_shortfall(observations: list[float], *, confidence: float = 0.95) -> dict:
    tail, reason = _tail(observations, confidence)
    if reason:
        return unavailable_result(reason, unit="ratio", input_refs=["periodic_returns", "confidence"])
    return _atom(
        max(0.0, -statistics.fmean(tail)),
        "risk.expected_shortfall.v1",
        refs=["periodic_returns", "confidence"],
    )


def correlation(left: list[float], right: list[float]) -> dict:
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right) or len(left) < 2:
        return unavailable_result(
            "at least two paired observations are required",
            unit="correlation",
            input_refs=["paired_left", "paired_right"],
        )
    x, x_reason = _numbers(left, 2)
    y, y_reason = _numbers(right, 2)
    if x_reason or y_reason:
        return unavailable_result(x_reason or y_reason, unit="correlation", input_refs=["paired_left", "paired_right"])
    x_dev = statistics.pstdev(x)
    y_dev = statistics.pstdev(y)
    if x_dev == 0 or y_dev == 0:
        return unavailable_result("paired variation must be nonzero", unit="correlation", input_refs=["paired_left", "paired_right"])
    x_mean, y_mean = statistics.fmean(x), statistics.fmean(y)
    covariance = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True)) / len(x)
    return _atom(covariance / (x_dev * y_dev), "risk.correlation.v1", unit="correlation", refs=["paired_left", "paired_right"])


def sharpe(observations: list[float], *, baseline_rate: float = 0.0, periods_per_year: float = 1.0) -> dict:
    values, reason = _numbers(observations, 2)
    if reason or periods_per_year <= 0:
        return unavailable_result(reason or "periods per year must be positive", unit="ratio", input_refs=["periodic_returns", "baseline_rate", "periods_per_year"])
    deviation = statistics.pstdev(values)
    if deviation == 0:
        return unavailable_result("return variation must be nonzero", unit="ratio", input_refs=["periodic_returns", "baseline_rate"])
    ratio = (statistics.fmean(values) - baseline_rate) / deviation * math.sqrt(periods_per_year)
    return _atom(ratio, "risk.sharpe.v1", refs=["periodic_returns", "baseline_rate", "periods_per_year"])


def sortino(observations: list[float], *, baseline_rate: float = 0.0, periods_per_year: float = 1.0) -> dict:
    values, reason = _numbers(observations, 1)
    if reason or periods_per_year <= 0:
        return unavailable_result(reason or "periods per year must be positive", unit="ratio", input_refs=["periodic_returns", "baseline_rate", "periods_per_year"])
    excess = [value - baseline_rate for value in values]
    downside = math.sqrt(sum(min(value, 0.0) ** 2 for value in excess) / len(excess))
    if downside == 0:
        return unavailable_result("downside deviation must be nonzero", unit="ratio", input_refs=["periodic_returns", "baseline_rate"])
    ratio = statistics.fmean(excess) / downside * math.sqrt(periods_per_year)
    return _atom(ratio, "risk.sortino.v1", refs=["periodic_returns", "baseline_rate", "periods_per_year"])


def calmar(annual_return: float, maximum_drawdown_value: float) -> dict:
    if maximum_drawdown_value <= 0:
        return unavailable_result("maximum drawdown must be positive", unit="ratio", input_refs=["annual_return", "maximum_drawdown"])
    return _atom(annual_return / maximum_drawdown_value, "risk.calmar.v1", refs=["annual_return", "maximum_drawdown"])


def return_to_drawdown(total_return: float, maximum_drawdown_value: float) -> dict:
    if maximum_drawdown_value <= 0:
        return unavailable_result("maximum drawdown must be positive", unit="ratio", input_refs=["total_return", "maximum_drawdown"])
    return _atom(total_return / maximum_drawdown_value, "risk.return_to_drawdown.v1", refs=["total_return", "maximum_drawdown"])
