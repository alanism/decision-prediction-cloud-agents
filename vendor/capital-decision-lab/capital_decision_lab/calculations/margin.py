"""Manual-input margin threshold and adverse-movement stress calculations."""

from __future__ import annotations

import math
from typing import Any

from capital_decision_lab.contracts.validation import unavailable_result


OUTPUT_UNITS = {
    "current_equity": "currency",
    "current_margin_ratio": "ratio",
    "loan_to_value": "ratio",
    "maintenance_margin_threshold": "currency",
    "estimated_margin_call_price": "currency per share",
    "liquidation_buffer": "currency per share",
    "liquidation_buffer_percent": "ratio",
    "margin_stress_table": "stress table",
    "margin_warning": "status",
}


def _atom(value: Any, name: str) -> dict:
    return {
        "value": value,
        "provenance_class": "calculated",
        "unit": OUTPUT_UNITS[name],
        "input_refs": ["margin_inputs"],
        "formula_ref": f"margin.{name}.v1",
        "limitations": ["Under supplied broker requirement assumptions"],
    }


def _unavailable(reason: str) -> dict[str, dict]:
    return {
        name: unavailable_result(reason, unit=unit, input_refs=["margin_inputs"])
        for name, unit in OUTPUT_UNITS.items()
    }


def _validate(values: dict) -> str | None:
    required = {
        "cash_equity",
        "position_market_value",
        "borrowed_amount",
        "maintenance_margin_requirement",
        "initial_margin_requirement",
        "current_price",
        "shares",
        "stress_price_declines",
    }
    if not isinstance(values, dict) or not required <= set(values):
        return "required margin inputs are missing"
    numeric = required - {"stress_price_declines"}
    if any(
        not isinstance(values[name], (int, float))
        or isinstance(values[name], bool)
        or not math.isfinite(float(values[name]))
        for name in numeric
    ):
        return "margin inputs must be finite numbers"
    if values["position_market_value"] <= 0 or values["current_price"] <= 0:
        return "market value and current price must be positive"
    if values["borrowed_amount"] < 0:
        return "borrowed amount must be nonnegative"
    if values["shares"] <= 0:
        return "shares must be greater than zero"
    if not 0 <= values["maintenance_margin_requirement"] < 1:
        return "maintenance requirement must be at least zero and below one"
    if not 0 <= values["initial_margin_requirement"] <= 1:
        return "initial requirement must be between zero and one"
    declines = values["stress_price_declines"]
    if (
        not isinstance(declines, list)
        or not declines
        or any(
            not isinstance(item, (int, float))
            or isinstance(item, bool)
            or not math.isfinite(float(item))
            or not 0 <= item < 1
            for item in declines
        )
    ):
        return "stress declines must be finite ratios from zero up to but not including one"
    return None


def analyze_margin(values: dict) -> dict[str, dict]:
    """Calculate current margin state, call threshold, and supplied stress rows."""
    reason = _validate(values)
    if reason:
        return _unavailable(reason)
    market_value = float(values["position_market_value"])
    borrowed = float(values["borrowed_amount"])
    maintenance = float(values["maintenance_margin_requirement"])
    current_price = float(values["current_price"])
    shares = float(values["shares"])
    equity = market_value - borrowed
    margin_ratio = equity / market_value
    loan_to_value = borrowed / market_value
    required_equity = maintenance * market_value
    call_price = borrowed / (shares * (1.0 - maintenance))
    buffer_value = current_price - call_price
    buffer_ratio = buffer_value / current_price
    rows: list[dict[str, Any]] = []
    for decline in values["stress_price_declines"]:
        stressed_price = current_price * (1.0 - float(decline))
        stressed_market_value = shares * stressed_price
        stressed_equity = stressed_market_value - borrowed
        stressed_margin_ratio = stressed_equity / stressed_market_value
        rows.append(
            {
                "price_decline": float(decline),
                "stressed_price": stressed_price,
                "stressed_market_value": stressed_market_value,
                "loss": market_value - stressed_market_value,
                "equity_remaining": stressed_equity,
                "margin_ratio": stressed_margin_ratio,
                "maintenance_breach": stressed_margin_ratio <= maintenance,
            }
        )
    if margin_ratio <= maintenance:
        warning = "current margin ratio is at or below the supplied maintenance threshold"
    elif margin_ratio - maintenance <= 0.05:
        warning = "current margin ratio is within 0.05 of the supplied maintenance threshold"
    elif any(row["maintenance_breach"] for row in rows):
        warning = "supplied stress scenarios reach the maintenance threshold"
    else:
        warning = "no threshold warning from supplied stress levels"
    return {
        "current_equity": _atom(equity, "current_equity"),
        "current_margin_ratio": _atom(margin_ratio, "current_margin_ratio"),
        "loan_to_value": _atom(loan_to_value, "loan_to_value"),
        "maintenance_margin_threshold": _atom(required_equity, "maintenance_margin_threshold"),
        "estimated_margin_call_price": _atom(call_price, "estimated_margin_call_price"),
        "liquidation_buffer": _atom(buffer_value, "liquidation_buffer"),
        "liquidation_buffer_percent": _atom(buffer_ratio, "liquidation_buffer_percent"),
        "margin_stress_table": _atom(rows, "margin_stress_table"),
        "margin_warning": _atom(warning, "margin_warning"),
    }
