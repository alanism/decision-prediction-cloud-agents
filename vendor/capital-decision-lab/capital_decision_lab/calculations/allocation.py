"""Kelly-based exposure calculations from explicit supplied inputs."""

from __future__ import annotations

import math

from capital_decision_lab.contracts.validation import unavailable_result


def _atom(value: float, formula_ref: str, refs: list[str]) -> dict:
    return {
        "value": value,
        "provenance_class": "calculated",
        "unit": "capital fraction",
        "input_refs": refs,
        "formula_ref": formula_ref,
        "limitations": ["Depends entirely on supplied probability and odds"],
    }


def _base(probability: float, net_odds: float) -> tuple[float | None, str | None]:
    if (
        not isinstance(probability, (int, float))
        or isinstance(probability, bool)
        or not math.isfinite(float(probability))
        or probability < 0
        or probability > 1
    ):
        return None, "probability must be between zero and one"
    if (
        not isinstance(net_odds, (int, float))
        or isinstance(net_odds, bool)
        or not math.isfinite(float(net_odds))
        or net_odds <= 0
    ):
        return None, "net odds must be greater than zero"
    loss_probability = 1.0 - float(probability)
    return (float(net_odds) * float(probability) - loss_probability) / float(net_odds), None


def kelly(probability: float, net_odds: float) -> dict:
    value, reason = _base(probability, net_odds)
    if reason:
        return unavailable_result(reason, unit="capital fraction", input_refs=["win_probability", "net_odds"])
    return _atom(value, "allocation.kelly.v1", ["win_probability", "net_odds"])


def fractional_kelly(probability: float, net_odds: float, fraction: float) -> dict:
    value, reason = _base(probability, net_odds)
    if reason:
        return unavailable_result(reason, unit="capital fraction", input_refs=["win_probability", "net_odds", "kelly_fraction"])
    if (
        not isinstance(fraction, (int, float))
        or isinstance(fraction, bool)
        or not math.isfinite(float(fraction))
        or not 0 < fraction <= 1
    ):
        return unavailable_result("fraction must be greater than zero and at most one", unit="capital fraction", input_refs=["kelly_fraction"])
    return _atom(value * float(fraction), "allocation.fractional_kelly.v1", ["win_probability", "net_odds", "kelly_fraction"])


def capped_fractional_kelly(
    probability: float,
    net_odds: float,
    fraction: float,
    exposure_cap: float,
) -> dict:
    fractional = fractional_kelly(probability, net_odds, fraction)
    if fractional["provenance_class"] == "unavailable":
        return fractional
    if (
        not isinstance(exposure_cap, (int, float))
        or isinstance(exposure_cap, bool)
        or not math.isfinite(float(exposure_cap))
        or not 0 <= exposure_cap <= 1
    ):
        return unavailable_result("exposure cap must be between zero and one", unit="capital fraction", input_refs=["exposure_cap"])
    value = min(max(float(fractional["value"]), 0.0), float(exposure_cap))
    return _atom(
        value,
        "allocation.capped_fractional_kelly.v1",
        ["win_probability", "net_odds", "kelly_fraction", "exposure_cap"],
    )


_STOCK_KELLY_OUTPUTS = {
    "full_kelly_fraction": "capital fraction",
    "confidence_adjusted_kelly": "capital fraction",
    "fractional_kelly_reference": "capital fraction",
    "capped_exposure": "capital fraction",
    "capped_exposure_amount": "currency",
    "kelly_edge": "payoff multiple",
    "expected_log_growth": "log growth",
    "kelly_warning": "status",
}


def _unavailable_kelly(reason: str) -> dict[str, dict]:
    return {
        name: unavailable_result(
            reason,
            unit=unit,
            input_refs=["kelly_stock_inputs"],
        )
        for name, unit in _STOCK_KELLY_OUTPUTS.items()
    }


def _validate_stock_kelly(values: dict) -> str | None:
    required = {
        "capital_at_risk",
        "win_probability",
        "win_payoff_multiple",
        "loss_probability",
        "loss_payoff_multiple",
        "kelly_fraction",
        "max_exposure_cap",
        "confidence_haircut",
    }
    if not isinstance(values, dict) or not required <= set(values):
        return "required Kelly inputs are missing"
    if any(
        not isinstance(values[name], (int, float))
        or isinstance(values[name], bool)
        or not math.isfinite(float(values[name]))
        for name in required
    ):
        return "Kelly inputs must be finite numbers"
    p = float(values["win_probability"])
    q = float(values["loss_probability"])
    if not 0 <= p <= 1 or not 0 <= q <= 1 or not math.isclose(p + q, 1.0, rel_tol=0.0, abs_tol=1e-12):
        return "win and loss probabilities must be valid and sum to one"
    if values["win_payoff_multiple"] <= 0 or values["loss_payoff_multiple"] >= 0:
        return "win payoff must be positive and loss payoff must be negative"
    if values["capital_at_risk"] < 0:
        return "capital at risk must be nonnegative"
    if not 0 < values["kelly_fraction"] <= 1:
        return "Kelly fraction must be greater than zero and at most one"
    if not 0 <= values["max_exposure_cap"] <= 1:
        return "user exposure cap must be between zero and one"
    if not 0 <= values["confidence_haircut"] <= 1:
        return "confidence haircut must be between zero and one"
    return None


def expected_log_growth(scenarios: list[dict], exposure: float) -> dict:
    """Calculate probability-weighted log growth for supplied scenario returns."""
    if not isinstance(scenarios, list) or not scenarios:
        return unavailable_result("at least one scenario is required", unit="log growth")
    if not isinstance(exposure, (int, float)) or isinstance(exposure, bool) or not math.isfinite(float(exposure)):
        return unavailable_result("exposure must be finite", unit="log growth")
    probability_total = 0.0
    growth = 0.0
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            return unavailable_result("scenario inputs are invalid", unit="log growth")
        probability = scenario.get("probability")
        payoff = scenario.get("payoff_multiple")
        if (
            not isinstance(probability, (int, float))
            or isinstance(probability, bool)
            or not isinstance(payoff, (int, float))
            or isinstance(payoff, bool)
            or not math.isfinite(float(probability))
            or not math.isfinite(float(payoff))
            or not 0 <= probability <= 1
            or 1.0 + float(exposure) * float(payoff) <= 0
        ):
            return unavailable_result("scenario log-growth inputs are outside the supported domain", unit="log growth")
        probability_total += float(probability)
        growth += float(probability) * math.log1p(float(exposure) * float(payoff))
    if not math.isclose(probability_total, 1.0, rel_tol=0.0, abs_tol=1e-12):
        return unavailable_result("scenario probabilities must sum to one", unit="log growth")
    return _atom(growth, "allocation.expected_log_growth.v1", ["kelly_scenarios", "exposure"])


def analyze_kelly(values: dict) -> dict[str, dict]:
    """Evaluate full, confidence-adjusted, fractional, and user-capped Kelly references."""
    reason = _validate_stock_kelly(values)
    if reason:
        return _unavailable_kelly(reason)
    p = float(values["win_probability"])
    q = float(values["loss_probability"])
    gain = float(values["win_payoff_multiple"])
    loss = float(values["loss_payoff_multiple"])
    edge = p * gain + q * loss
    full = -(edge) / (gain * loss)
    adjusted = full * float(values["confidence_haircut"])
    fractional = adjusted * float(values["kelly_fraction"])
    capped = min(max(fractional, 0.0), float(values["max_exposure_cap"]))
    scenarios = [
        {"probability": p, "payoff_multiple": gain},
        {"probability": q, "payoff_multiple": loss},
    ]
    log_growth = expected_log_growth(scenarios, capped)
    if edge < 0:
        warning = "negative edge under supplied assumptions"
    elif math.isclose(edge, 0.0, rel_tol=0.0, abs_tol=1e-12):
        warning = "zero edge under supplied assumptions"
    elif full > float(values["max_exposure_cap"]):
        warning = "calculated full Kelly exceeds the user cap"
    elif adjusted <= float(values["max_exposure_cap"]) * 0.05:
        warning = "edge is fragile after confidence haircut"
    else:
        warning = "no Kelly threshold warning under supplied assumptions"
    refs = ["kelly_stock_inputs"]
    result = {
        "full_kelly_fraction": _atom(full, "allocation.stock_full_kelly.v1", refs),
        "confidence_adjusted_kelly": _atom(adjusted, "allocation.confidence_adjusted_kelly.v1", refs),
        "fractional_kelly_reference": _atom(fractional, "allocation.stock_fractional_kelly.v1", refs),
        "capped_exposure": _atom(capped, "allocation.user_capped_exposure.v1", refs),
        "capped_exposure_amount": {
            **_atom(capped * float(values["capital_at_risk"]), "allocation.capped_exposure_amount.v1", refs),
            "unit": "currency",
        },
        "kelly_edge": {
            **_atom(edge, "allocation.kelly_edge.v1", refs),
            "unit": "payoff multiple",
        },
        "expected_log_growth": log_growth,
        "kelly_warning": {
            **_atom(warning, "allocation.kelly_warning.v1", refs),
            "unit": "status",
        },
    }
    return result
