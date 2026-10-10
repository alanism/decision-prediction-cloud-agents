from __future__ import annotations

import math

import pytest

from capital_decision_lab.calculations import allocation
from capital_decision_lab.contracts.validation import validate_evidence_atom


def _inputs(**overrides) -> dict:
    values = {
        "capital_at_risk": 10000.0,
        "win_probability": 0.35,
        "win_payoff_multiple": 3.0,
        "loss_probability": 0.65,
        "loss_payoff_multiple": -1.0,
        "kelly_fraction": 0.25,
        "max_exposure_cap": 0.1,
        "confidence_haircut": 0.5,
    }
    values.update(overrides)
    return values


def test_stock_kelly_outputs_are_provenance_labeled() -> None:
    result = allocation.analyze_kelly(_inputs())
    assert all(validate_evidence_atom(atom) == [] for atom in result.values())
    assert result["full_kelly_fraction"]["value"] == pytest.approx(2.0 / 15.0)
    assert result["confidence_adjusted_kelly"]["value"] == pytest.approx(1.0 / 15.0)
    assert result["fractional_kelly_reference"]["value"] == pytest.approx(1.0 / 60.0)
    assert result["capped_exposure"]["value"] == pytest.approx(1.0 / 60.0)
    assert result["capped_exposure_amount"]["value"] == pytest.approx(10000.0 / 60.0)
    expected_log = 0.35 * math.log1p((1.0 / 60.0) * 3.0) + 0.65 * math.log1p((1.0 / 60.0) * -1.0)
    assert result["expected_log_growth"]["value"] == pytest.approx(expected_log)


def test_excessive_kelly_and_confidence_haircut() -> None:
    result = allocation.analyze_kelly(_inputs())
    assert result["full_kelly_fraction"]["value"] > _inputs()["max_exposure_cap"]
    assert result["confidence_adjusted_kelly"]["value"] < result["full_kelly_fraction"]["value"]
    assert result["kelly_warning"]["value"] == "calculated full Kelly exceeds the user cap"


def test_negative_and_zero_edge_do_not_create_positive_exposure() -> None:
    negative = allocation.analyze_kelly(
        _inputs(win_probability=0.2, loss_probability=0.8, win_payoff_multiple=1.0)
    )
    zero = allocation.analyze_kelly(
        _inputs(win_probability=0.5, loss_probability=0.5, win_payoff_multiple=1.0)
    )
    assert negative["full_kelly_fraction"]["value"] < 0
    assert negative["capped_exposure"]["value"] == 0.0
    assert negative["kelly_warning"]["value"] == "negative edge under supplied assumptions"
    assert zero["full_kelly_fraction"]["value"] == 0.0
    assert zero["capped_exposure"]["value"] == 0.0
    assert zero["kelly_warning"]["value"] == "zero edge under supplied assumptions"


def test_invalid_probability_and_payoff_inputs_are_unavailable() -> None:
    invalid_cases = [
        _inputs(win_probability=0.5, loss_probability=0.6),
        _inputs(win_payoff_multiple=0.0),
        _inputs(loss_payoff_multiple=0.1),
        _inputs(confidence_haircut=1.2),
    ]
    for values in invalid_cases:
        result = allocation.analyze_kelly(values)
        assert result["full_kelly_fraction"]["provenance_class"] == "unavailable"
        assert result["capped_exposure"]["provenance_class"] == "unavailable"
        assert result["full_kelly_fraction"]["reason"]


def test_fragile_edge_warning_after_confidence_haircut() -> None:
    result = allocation.analyze_kelly(
        _inputs(max_exposure_cap=0.5, confidence_haircut=0.05)
    )
    assert result["confidence_adjusted_kelly"]["value"] > 0
    assert result["kelly_warning"]["value"] == "edge is fragile after confidence haircut"


def test_multi_scenario_expected_log_growth() -> None:
    scenarios = [
        {"probability": 0.2, "payoff_multiple": 4.0},
        {"probability": 0.5, "payoff_multiple": 0.5},
        {"probability": 0.3, "payoff_multiple": -1.0},
    ]
    result = allocation.expected_log_growth(scenarios, 0.1)
    expected = sum(item["probability"] * math.log1p(0.1 * item["payoff_multiple"]) for item in scenarios)
    assert result["value"] == pytest.approx(expected)
    assert validate_evidence_atom(result) == []
