"""Deterministic orchestration of approved calculation engines."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from capital_decision_lab.calculations import allocation, convexity, margin, returns, risk, simulation
from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash
from capital_decision_lab.contracts.validation import unavailable_result


METRIC_NAMES = (
    "absolute_gain_loss", "roi", "cagr", "expected_value", "expected_return",
    "volatility", "downside_deviation", "maximum_drawdown", "loss_probability",
    "value_at_risk", "expected_shortfall", "correlation", "sharpe", "sortino",
    "calmar", "return_to_drawdown", "kelly", "fractional_kelly",
    "capped_fractional_kelly", "scenario_bull", "scenario_base", "scenario_bear",
    "scenario_expected_return", "terminal_p05", "terminal_p50", "terminal_p95",
    "terminal_mean", "simulation_loss_probability",
    "full_kelly_fraction", "confidence_adjusted_kelly", "fractional_kelly_reference",
    "capped_exposure", "capped_exposure_amount", "kelly_edge", "expected_log_growth",
    "kelly_warning", "upside_downside_multiple", "breakeven_probability",
    "convexity_expected_value", "convexity_expected_return", "payoff_skew",
    "probability_weighted_upside", "probability_weighted_downside", "downside_severity",
    "max_loss", "convexity_score", "scenario_dispersion", "tail_upside",
    "tail_downside", "scenario_table", "optionality_note", "current_equity",
    "current_margin_ratio", "loan_to_value", "maintenance_margin_threshold",
    "estimated_margin_call_price", "liquidation_buffer", "liquidation_buffer_percent",
    "margin_stress_table", "margin_warning",
)

KELLY_METRICS = (
    "full_kelly_fraction", "confidence_adjusted_kelly", "fractional_kelly_reference",
    "capped_exposure", "capped_exposure_amount", "kelly_edge", "expected_log_growth",
    "kelly_warning",
)
CONVEXITY_METRICS = (
    "upside_downside_multiple", "breakeven_probability", "convexity_expected_value",
    "convexity_expected_return", "payoff_skew", "probability_weighted_upside",
    "probability_weighted_downside", "downside_severity", "max_loss", "convexity_score",
    "scenario_dispersion", "tail_upside", "tail_downside", "scenario_table", "optionality_note",
)
MARGIN_METRICS = (
    "current_equity", "current_margin_ratio", "loan_to_value",
    "maintenance_margin_threshold", "estimated_margin_call_price", "liquidation_buffer",
    "liquidation_buffer_percent", "margin_stress_table", "margin_warning",
)


def _unavailable(name: str, reason: str = "required inputs are unavailable") -> dict:
    return unavailable_result(reason, input_refs=[name])


def _call(name: str, function: Callable, *args, **kwargs) -> dict:
    try:
        return function(*args, **kwargs)
    except (TypeError, ValueError, OverflowError):
        return _unavailable(name, "supplied inputs are invalid")


def _value(inputs: dict, name: str, default: Any = None) -> Any:
    atom = inputs.get(name)
    return atom.get("value", default) if isinstance(atom, dict) else default


def _merged_inputs(case: dict, alternative_id: str | None) -> dict:
    merged = dict(case.get("inputs", {}))
    if alternative_id is not None:
        alternative = next(
            (item for item in case.get("alternatives", []) if item.get("alternative_id") == alternative_id),
            None,
        )
        if alternative is None:
            raise ValueError("ALTERNATIVE_UNKNOWN")
        merged.update(alternative.get("inputs", {}))
    return merged


def analyze_case(case: dict, *, alternative_id: str | None = None) -> dict:
    inputs = _merged_inputs(case, alternative_id)
    data = {name: _unavailable(name) for name in METRIC_NAMES}
    starting = _value(inputs, "starting_value")
    ending = _value(inputs, "ending_value")
    years = _value(inputs, "years")
    outcomes = _value(inputs, "outcomes")
    periodic = _value(inputs, "periodic_returns")
    levels = _value(inputs, "value_series")
    paired = _value(inputs, "paired_returns")
    baseline = _value(inputs, "baseline_rate", 0.0)
    annualization = _value(inputs, "periods_per_year", 1.0)
    confidence = _value(inputs, "confidence", 0.95)

    if starting is not None and ending is not None:
        unit = inputs.get("starting_value", {}).get("unit", "currency")
        data["absolute_gain_loss"] = _call("absolute_gain_loss", returns.absolute_gain_loss, starting, ending, unit=unit)
        data["roi"] = _call("roi", returns.roi, starting, ending)
    if starting is not None and ending is not None and years is not None:
        data["cagr"] = _call("cagr", returns.cagr, starting, ending, years)
    if outcomes is not None:
        data["expected_value"] = _call("expected_value", returns.expected_value, outcomes)
        data["expected_return"] = _call("expected_return", returns.expected_return, outcomes)
    if periodic is not None:
        data["volatility"] = _call("volatility", risk.volatility, periodic)
        data["downside_deviation"] = _call("downside_deviation", risk.downside_deviation, periodic)
        data["loss_probability"] = _call("loss_probability", risk.loss_probability, periodic)
        data["value_at_risk"] = _call("value_at_risk", risk.value_at_risk, periodic, confidence=confidence)
        data["expected_shortfall"] = _call("expected_shortfall", risk.expected_shortfall, periodic, confidence=confidence)
        data["sharpe"] = _call("sharpe", risk.sharpe, periodic, baseline_rate=baseline, periods_per_year=annualization)
        data["sortino"] = _call("sortino", risk.sortino, periodic, baseline_rate=baseline, periods_per_year=annualization)
    if levels is not None:
        data["maximum_drawdown"] = _call("maximum_drawdown", risk.maximum_drawdown, levels)
    if isinstance(paired, dict):
        data["correlation"] = _call("correlation", risk.correlation, paired.get("left"), paired.get("right"))
    if data["cagr"]["value"] is not None and data["maximum_drawdown"]["value"] is not None:
        data["calmar"] = _call("calmar", risk.calmar, data["cagr"]["value"], data["maximum_drawdown"]["value"])
    if data["roi"]["value"] is not None and data["maximum_drawdown"]["value"] is not None:
        data["return_to_drawdown"] = _call("return_to_drawdown", risk.return_to_drawdown, data["roi"]["value"], data["maximum_drawdown"]["value"])

    probability = _value(inputs, "win_probability")
    odds = _value(inputs, "net_odds")
    fraction = _value(inputs, "kelly_fraction")
    cap = _value(inputs, "exposure_cap")
    if probability is not None and odds is not None:
        data["kelly"] = _call("kelly", allocation.kelly, probability, odds)
    if probability is not None and odds is not None and fraction is not None:
        data["fractional_kelly"] = _call("fractional_kelly", allocation.fractional_kelly, probability, odds, fraction)
    if probability is not None and odds is not None and fraction is not None and cap is not None:
        data["capped_fractional_kelly"] = _call("capped_fractional_kelly", allocation.capped_fractional_kelly, probability, odds, fraction, cap)

    scenario_input = _value(inputs, "scenarios")
    if scenario_input is not None:
        scenario_result = simulation.scenario_analysis(scenario_input)
        for name in ("scenario_bull", "scenario_base", "scenario_bear", "scenario_expected_return"):
            if name in scenario_result["data"]:
                data[name] = scenario_result["data"][name]

    simulation_metadata: dict = {}
    simulation_input = _value(inputs, "simulation")
    if isinstance(simulation_input, dict):
        simulation_result = _call("simulation_result", simulation.monte_carlo, **simulation_input)
        if "data" in simulation_result:
            for name in ("terminal_p05", "terminal_p50", "terminal_p95", "terminal_mean", "simulation_loss_probability"):
                if name in simulation_result["data"]:
                    data[name] = simulation_result["data"][name]
            simulation_metadata = simulation_result.get("metadata", {})

    kelly_input = _value(inputs, "kelly_stock")
    if isinstance(kelly_input, dict):
        data.update(allocation.analyze_kelly(kelly_input))

    convexity_input = _value(inputs, "convexity_scenarios")
    if isinstance(convexity_input, dict):
        convexity_result = convexity.analyze_convexity(convexity_input)
        convexity_mapping = {
            "expected_value": "convexity_expected_value",
            "expected_return": "convexity_expected_return",
        }
        for name, atom in convexity_result.items():
            data[convexity_mapping.get(name, name)] = atom

    margin_input = _value(inputs, "margin_inputs")
    if isinstance(margin_input, dict):
        data.update(margin.analyze_margin(margin_input))

    case_hash = contract_payload_hash(case)
    identity = {"case_id": case["case_id"], "alternative_id": alternative_id}
    document = {
        "contract_version": "nhi.decision_analysis.v1",
        "analysis_id": f"analysis_{canonical_sha256(identity)[:16]}",
        "alternative_id": alternative_id,
        "case_ref": {"id": case["case_id"], "canonical_hash": case_hash},
        "data": data,
        "simulation_metadata": simulation_metadata,
        "report_sections": {
            "decision_summary": [
                "absolute_gain_loss", "roi", "cagr", "expected_value", "expected_return",
                "volatility", "maximum_drawdown", "sharpe", "sortino", "calmar",
            ],
            "kelly_sizing": list(KELLY_METRICS),
            "convexity_upside_asymmetry": list(CONVEXITY_METRICS),
            "margin_safety": list(MARGIN_METRICS),
            "scenario_analysis": [
                "scenario_bull", "scenario_base", "scenario_bear",
                "scenario_expected_return", "terminal_p05", "terminal_p50", "terminal_p95",
            ],
            "unavailable_metrics": [
                name for name, atom in data.items() if atom["provenance_class"] == "unavailable"
            ],
            "warnings": ["kelly_warning", "margin_warning"],
            "provenance_and_hashes": {
                "case_hash": case_hash,
                "provenance_classes": [
                    "measured", "assumed", "calculated", "modeled", "forecast", "decided", "unavailable"
                ],
            },
        },
    }
    document["canonical_hash"] = contract_payload_hash(document)
    return document
