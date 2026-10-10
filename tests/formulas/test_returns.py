from __future__ import annotations

import pytest

from capital_decision_lab.calculations import returns
from capital_decision_lab.contracts.validation import validate_evidence_atom


def _value(atom: dict) -> float:
    assert validate_evidence_atom(atom) == []
    assert atom["provenance_class"] in {"calculated", "unavailable"}
    return atom["value"]


def test_absolute_gain_loss_and_roi() -> None:
    gain = returns.absolute_gain_loss(100.0, 120.0, unit="USD")
    roi = returns.roi(100.0, 120.0)
    assert _value(gain) == pytest.approx(20.0)
    assert gain["unit"] == "USD"
    assert gain["formula_ref"] == "return.absolute_gain_loss.v1"
    assert _value(roi) == pytest.approx(0.2)
    assert roi["unit"] == "ratio"


def test_roi_zero_denominator_is_unavailable() -> None:
    result = returns.roi(0.0, 120.0)
    assert result["value"] is None
    assert result["provenance_class"] == "unavailable"
    assert result["reason"] == "starting value must be nonzero"


def test_cagr_and_invalid_horizon() -> None:
    assert _value(returns.cagr(100.0, 121.0, 2.0)) == pytest.approx(0.1)
    invalid = returns.cagr(100.0, 121.0, 0.0)
    assert invalid["provenance_class"] == "unavailable"
    assert invalid["reason"] == "years must be greater than zero"


def test_expected_value_and_expected_return() -> None:
    outcomes = [
        {"probability": 0.6, "payoff": 100.0, "return": 0.2},
        {"probability": 0.4, "payoff": -50.0, "return": -0.1},
    ]
    assert _value(returns.expected_value(outcomes, unit="USD")) == pytest.approx(40.0)
    assert _value(returns.expected_return(outcomes)) == pytest.approx(0.08)


def test_expected_metrics_reject_invalid_probabilities() -> None:
    outcomes = [
        {"probability": 0.8, "payoff": 100.0, "return": 0.2},
        {"probability": 0.5, "payoff": -50.0, "return": -0.1},
    ]
    for result in (returns.expected_value(outcomes), returns.expected_return(outcomes)):
        assert result["value"] is None
        assert result["provenance_class"] == "unavailable"
        assert result["reason"] == "probabilities must sum to one"
