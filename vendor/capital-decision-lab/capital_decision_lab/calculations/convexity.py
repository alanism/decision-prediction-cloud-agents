"""Scenario-based convexity and upside-asymmetry calculations."""

from __future__ import annotations

import math
from typing import Any

from capital_decision_lab.contracts.validation import unavailable_result


OUTPUT_UNITS = {
    "upside_downside_multiple": "multiple",
    "breakeven_probability": "probability",
    "expected_value": "currency",
    "expected_return": "ratio",
    "payoff_skew": "skew",
    "probability_weighted_upside": "currency",
    "probability_weighted_downside": "currency",
    "downside_severity": "currency",
    "max_loss": "currency",
    "convexity_score": "multiple",
    "scenario_dispersion": "currency",
    "tail_upside": "currency",
    "tail_downside": "currency",
    "scenario_table": "scenario set",
    "optionality_note": "status",
}


def _atom(
    value: Any,
    name: str,
    *,
    provenance: str = "calculated",
    limitations: list[str] | None = None,
) -> dict:
    return {
        "value": value,
        "provenance_class": provenance,
        "unit": OUTPUT_UNITS[name],
        "input_refs": ["convexity_scenarios"],
        "formula_ref": f"convexity.{name}.v1",
        "limitations": limitations or ["Calculated only from supplied scenario assumptions"],
    }


def _unavailable(reason: str) -> dict[str, dict]:
    return {
        name: unavailable_result(
            reason,
            unit=unit,
            input_refs=["convexity_scenarios"],
        )
        for name, unit in OUTPUT_UNITS.items()
    }


def _validate(values: dict) -> tuple[list[dict] | None, str | None]:
    if not isinstance(values, dict) or not isinstance(values.get("scenarios"), list) or not values["scenarios"]:
        return None, "at least one scenario is required"
    scenarios = values["scenarios"]
    names: set[str] = set()
    total = 0.0
    for scenario in scenarios:
        required = {"name", "probability", "payoff", "return"}
        if not isinstance(scenario, dict) or not required <= set(scenario):
            return None, "scenario fields are missing"
        if not isinstance(scenario["name"], str) or not scenario["name"] or scenario["name"] in names:
            return None, "scenario names must be unique"
        names.add(scenario["name"])
        for key in ("probability", "payoff", "return"):
            value = scenario[key]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
                return None, "scenario values must be finite numbers"
        if not 0 <= scenario["probability"] <= 1:
            return None, "scenario probabilities must be between zero and one"
        total += float(scenario["probability"])
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
        return None, "scenario probabilities must sum to one"
    return scenarios, None


def analyze_convexity(values: dict) -> dict[str, dict]:
    """Measure payoff asymmetry without selecting or ranking an exposure."""
    scenarios, reason = _validate(values)
    if reason:
        return _unavailable(reason)
    expected_value = sum(float(item["probability"]) * float(item["payoff"]) for item in scenarios)
    expected_return = sum(float(item["probability"]) * float(item["return"]) for item in scenarios)
    weighted_upside = sum(
        float(item["probability"]) * float(item["payoff"])
        for item in scenarios
        if item["payoff"] > 0
    )
    weighted_downside = abs(
        sum(
            float(item["probability"]) * float(item["payoff"])
            for item in scenarios
            if item["payoff"] < 0
        )
    )
    positive = [float(item["payoff"]) for item in scenarios if item["payoff"] > 0]
    negative = [float(item["payoff"]) for item in scenarios if item["payoff"] < 0]
    mean = expected_value
    variance = sum(
        float(item["probability"]) * (float(item["payoff"]) - mean) ** 2
        for item in scenarios
    )
    dispersion = math.sqrt(variance)
    third = sum(
        float(item["probability"]) * (float(item["payoff"]) - mean) ** 3
        for item in scenarios
    )
    skew = third / dispersion**3 if dispersion > 0 else None
    bear = next((item for item in scenarios if item["name"] == "bear"), None)
    bull = next((item for item in scenarios if item["name"] == "bull"), None)
    bear_loss = abs(float(bear["payoff"])) if bear and bear["payoff"] < 0 else 0.0
    bull_gain = float(bull["payoff"]) if bull and bull["payoff"] > 0 else 0.0

    result = {
        "expected_value": _atom(expected_value, "expected_value"),
        "expected_return": _atom(expected_return, "expected_return"),
        "probability_weighted_upside": _atom(weighted_upside, "probability_weighted_upside"),
        "probability_weighted_downside": _atom(weighted_downside, "probability_weighted_downside"),
        "downside_severity": _atom(max((abs(value) for value in negative), default=0.0), "downside_severity"),
        "max_loss": _atom(max((abs(value) for value in negative), default=0.0), "max_loss"),
        "scenario_dispersion": _atom(dispersion, "scenario_dispersion"),
        "tail_upside": _atom(max(positive, default=0.0), "tail_upside"),
        "tail_downside": _atom(max((abs(value) for value in negative), default=0.0), "tail_downside"),
        "scenario_table": _atom(
            scenarios,
            "scenario_table",
            provenance="modeled",
            limitations=["Scenario values and probabilities are supplied assumptions"],
        ),
        "optionality_note": _atom(
            "capped downside and open-ended upside are supplied assumptions"
            if values.get("downside_capped") is True and values.get("upside_open_ended") is True
            else "optionality conditions were not both supplied",
            "optionality_note",
            provenance="modeled",
        ),
    }
    result["payoff_skew"] = (
        _atom(skew, "payoff_skew")
        if skew is not None
        else unavailable_result("scenario dispersion must be nonzero", unit="skew", input_refs=["convexity_scenarios"])
    )
    if bear_loss == 0 or bull_gain == 0:
        result["upside_downside_multiple"] = unavailable_result(
            "positive bull payoff and negative bear payoff are required",
            unit="multiple",
            input_refs=["convexity_scenarios"],
        )
        result["breakeven_probability"] = unavailable_result(
            "positive bull payoff and negative bear payoff are required",
            unit="probability",
            input_refs=["convexity_scenarios"],
        )
    else:
        result["upside_downside_multiple"] = _atom(
            bull_gain / bear_loss, "upside_downside_multiple"
        )
        result["breakeven_probability"] = _atom(
            bear_loss / (bull_gain + bear_loss), "breakeven_probability"
        )
    result["convexity_score"] = (
        _atom(weighted_upside / weighted_downside, "convexity_score")
        if weighted_downside > 0
        else unavailable_result(
            "probability-weighted downside must be positive",
            unit="multiple",
            input_refs=["convexity_scenarios"],
        )
    )
    return result
