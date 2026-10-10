"""Deterministic return calculations with evidence-atom outputs."""

from __future__ import annotations

import math
from typing import Any

from capital_decision_lab.contracts.validation import unavailable_result


def _atom(value: float, *, unit: str, formula_ref: str, input_refs: list[str]) -> dict:
    return {
        "value": value,
        "provenance_class": "calculated",
        "unit": unit,
        "input_refs": input_refs,
        "formula_ref": formula_ref,
        "limitations": ["Calculated only from supplied inputs"],
    }


def absolute_gain_loss(starting_value: float, ending_value: float, *, unit: str = "currency") -> dict:
    return _atom(
        ending_value - starting_value,
        unit=unit,
        formula_ref="return.absolute_gain_loss.v1",
        input_refs=["starting_value", "ending_value"],
    )


def roi(starting_value: float, ending_value: float) -> dict:
    if starting_value == 0:
        return unavailable_result(
            "starting value must be nonzero",
            unit="ratio",
            input_refs=["starting_value", "ending_value"],
        )
    return _atom(
        (ending_value - starting_value) / starting_value,
        unit="ratio",
        formula_ref="return.roi.v1",
        input_refs=["starting_value", "ending_value"],
    )


def cagr(starting_value: float, ending_value: float, years: float) -> dict:
    if years <= 0:
        return unavailable_result(
            "years must be greater than zero",
            unit="annual ratio",
            input_refs=["starting_value", "ending_value", "years"],
        )
    if starting_value <= 0 or ending_value < 0:
        return unavailable_result(
            "values are outside the supported compounding domain",
            unit="annual ratio",
            input_refs=["starting_value", "ending_value", "years"],
        )
    value = math.pow(ending_value / starting_value, 1.0 / years) - 1.0
    return _atom(
        value,
        unit="annual ratio",
        formula_ref="return.cagr.v1",
        input_refs=["starting_value", "ending_value", "years"],
    )


def _validate_outcomes(outcomes: Any, value_key: str) -> str | None:
    if not isinstance(outcomes, list) or not outcomes:
        return "at least one outcome is required"
    probabilities: list[float] = []
    for outcome in outcomes:
        if not isinstance(outcome, dict) or "probability" not in outcome or value_key not in outcome:
            return f"each outcome requires probability and {value_key}"
        probability = outcome["probability"]
        value = outcome[value_key]
        if (
            not isinstance(probability, (int, float))
            or isinstance(probability, bool)
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(probability))
            or not math.isfinite(float(value))
        ):
            return "outcome values must be finite numbers"
        if probability < 0 or probability > 1:
            return "probabilities must be between zero and one"
        probabilities.append(float(probability))
    if not math.isclose(sum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-12):
        return "probabilities must sum to one"
    return None


def expected_value(outcomes: list[dict], *, unit: str = "currency") -> dict:
    reason = _validate_outcomes(outcomes, "payoff")
    if reason:
        return unavailable_result(reason, unit=unit, input_refs=["outcomes"])
    value = sum(float(item["probability"]) * float(item["payoff"]) for item in outcomes)
    return _atom(
        value,
        unit=unit,
        formula_ref="return.expected_value.v1",
        input_refs=["outcomes"],
    )


def expected_return(outcomes: list[dict]) -> dict:
    reason = _validate_outcomes(outcomes, "return")
    if reason:
        return unavailable_result(reason, unit="ratio", input_refs=["outcomes"])
    value = sum(float(item["probability"]) * float(item["return"]) for item in outcomes)
    return _atom(
        value,
        unit="ratio",
        formula_ref="return.expected_return.v1",
        input_refs=["outcomes"],
    )
