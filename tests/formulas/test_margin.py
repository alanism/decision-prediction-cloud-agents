from __future__ import annotations

import pytest

from capital_decision_lab.calculations import margin
from capital_decision_lab.contracts.validation import validate_evidence_atom


def _inputs(**overrides) -> dict:
    values = {
        "cash_equity": 10000.0,
        "position_market_value": 20000.0,
        "borrowed_amount": 10000.0,
        "maintenance_margin_requirement": 0.25,
        "initial_margin_requirement": 0.5,
        "current_price": 100.0,
        "shares": 200.0,
        "stress_price_declines": [0.1, 0.2, 0.3, 0.4, 0.5],
    }
    values.update(overrides)
    return values


def test_margin_metrics_and_call_threshold() -> None:
    result = margin.analyze_margin(_inputs())
    assert all(validate_evidence_atom(atom) == [] for atom in result.values())
    assert result["current_equity"]["value"] == 10000.0
    assert result["current_margin_ratio"]["value"] == pytest.approx(0.5)
    assert result["loan_to_value"]["value"] == pytest.approx(0.5)
    assert result["maintenance_margin_threshold"]["value"] == 5000.0
    assert result["estimated_margin_call_price"]["value"] == pytest.approx(10000.0 / 150.0)
    assert result["liquidation_buffer"]["value"] == pytest.approx(100.0 - 10000.0 / 150.0)
    assert result["liquidation_buffer_percent"]["value"] == pytest.approx(1.0 / 3.0)


def test_margin_stress_table_and_breach_warning() -> None:
    result = margin.analyze_margin(_inputs())
    table = result["margin_stress_table"]
    assert table["provenance_class"] == "calculated"
    assert len(table["value"]) == 5
    assert table["value"][-1]["stressed_price"] == 50.0
    assert table["value"][-1]["loss"] == 10000.0
    assert table["value"][-1]["equity_remaining"] == 0.0
    assert table["value"][-1]["maintenance_breach"] is True
    assert result["margin_warning"]["value"] == "supplied stress scenarios reach the maintenance threshold"


def test_current_margin_breach_has_stronger_warning() -> None:
    result = margin.analyze_margin(
        _inputs(position_market_value=12000.0, borrowed_amount=10000.0)
    )
    assert result["current_margin_ratio"]["value"] < 0.25
    assert result["margin_warning"]["value"] == "current margin ratio is at or below the supplied maintenance threshold"


def test_invalid_shares_and_maintenance_are_unavailable() -> None:
    for values in (_inputs(shares=0.0), _inputs(maintenance_margin_requirement=1.0)):
        result = margin.analyze_margin(values)
        assert result["estimated_margin_call_price"]["provenance_class"] == "unavailable"
        assert result["margin_stress_table"]["provenance_class"] == "unavailable"
        assert result["estimated_margin_call_price"]["reason"]


def test_margin_output_avoids_assurance_wording() -> None:
    result = margin.analyze_margin(_inputs())
    output = str(result).lower()
    assert "safe to use margin" not in output
    assert "guaranteed no margin call" not in output
    assert "recommended leverage" not in output
