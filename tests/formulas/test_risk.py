from __future__ import annotations

import math
import statistics

import pytest

from capital_decision_lab.calculations import risk
from capital_decision_lab.contracts.validation import validate_evidence_atom


def _value(atom: dict) -> float:
    assert validate_evidence_atom(atom) == []
    return atom["value"]


def test_volatility_downside_deviation_and_loss_probability() -> None:
    observations = [0.1, -0.05, 0.2, -0.1]
    assert _value(risk.volatility(observations)) == pytest.approx(statistics.pstdev(observations))
    assert _value(risk.downside_deviation(observations)) == pytest.approx(math.sqrt(0.0125 / 4))
    assert _value(risk.loss_probability(observations)) == pytest.approx(0.5)


def test_maximum_drawdown_uses_peak_to_trough_direction() -> None:
    result = risk.maximum_drawdown([100.0, 120.0, 90.0, 110.0, 80.0])
    assert _value(result) == pytest.approx(1.0 / 3.0)
    assert result["formula_ref"] == "risk.maximum_drawdown.v1"


def test_historical_value_at_risk_and_expected_shortfall() -> None:
    observations = [0.1, -0.05, 0.2, -0.1]
    assert _value(risk.value_at_risk(observations, confidence=0.75)) == pytest.approx(0.1)
    assert _value(risk.expected_shortfall(observations, confidence=0.75)) == pytest.approx(0.1)


def test_correlation_and_insufficient_pairs() -> None:
    assert _value(risk.correlation([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])) == pytest.approx(1.0)
    unavailable = risk.correlation([1.0], [2.0])
    assert unavailable["provenance_class"] == "unavailable"
    assert unavailable["reason"] == "at least two paired observations are required"


def test_sharpe_and_annualization() -> None:
    observations = [0.02, 0.04, 0.0]
    base = risk.sharpe(observations, baseline_rate=0.01)
    annual = risk.sharpe(observations, baseline_rate=0.01, periods_per_year=12)
    assert _value(base) == pytest.approx(0.01 / statistics.pstdev(observations))
    assert _value(annual) == pytest.approx(_value(base) * math.sqrt(12))


def test_sortino_calmar_and_return_to_drawdown() -> None:
    observations = [0.02, 0.04, 0.0]
    assert _value(risk.sortino(observations, baseline_rate=0.01)) == pytest.approx(math.sqrt(3))
    assert _value(risk.calmar(0.12, 0.2)) == pytest.approx(0.6)
    assert _value(risk.return_to_drawdown(0.15, 0.25)) == pytest.approx(0.6)


def test_invalid_or_insufficient_risk_inputs_are_unavailable() -> None:
    cases = [
        risk.volatility([0.1]),
        risk.maximum_drawdown([]),
        risk.value_at_risk([0.1], confidence=1.0),
        risk.correlation([1.0, 1.0], [2.0, 3.0]),
        risk.sharpe([0.1, 0.1]),
        risk.calmar(0.1, 0.0),
    ]
    assert all(item["provenance_class"] == "unavailable" for item in cases)
