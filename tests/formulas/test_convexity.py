from __future__ import annotations

import pytest

from capital_decision_lab.calculations import convexity
from capital_decision_lab.contracts.validation import validate_evidence_atom


def _scenarios() -> dict:
    return {
        "scenarios": [
            {"name": "bear", "probability": 0.25, "payoff": -40.0, "return": -0.4},
            {"name": "base", "probability": 0.35, "payoff": 10.0, "return": 0.1},
            {"name": "bull", "probability": 0.25, "payoff": 100.0, "return": 1.0},
            {"name": "moonshot", "probability": 0.15, "payoff": 400.0, "return": 4.0},
        ],
        "downside_capped": True,
        "upside_open_ended": True,
    }


def test_convexity_metrics_and_evidence_atoms() -> None:
    result = convexity.analyze_convexity(_scenarios())
    assert all(validate_evidence_atom(atom) == [] for atom in result.values())
    assert result["upside_downside_multiple"]["value"] == pytest.approx(2.5)
    assert result["breakeven_probability"]["value"] == pytest.approx(40.0 / 140.0)
    assert result["expected_value"]["value"] == pytest.approx(78.5)
    assert result["expected_return"]["value"] == pytest.approx(0.785)
    assert result["probability_weighted_upside"]["value"] == pytest.approx(88.5)
    assert result["probability_weighted_downside"]["value"] == pytest.approx(10.0)
    assert result["convexity_score"]["value"] == pytest.approx(8.85)
    assert result["tail_upside"]["value"] == 400.0
    assert result["tail_downside"]["value"] == 40.0


def test_scenario_table_is_modeled_and_does_not_assert_targets_as_facts() -> None:
    result = convexity.analyze_convexity(_scenarios())
    table = result["scenario_table"]
    assert table["provenance_class"] == "modeled"
    assert len(table["value"]) == 4
    assert result["optionality_note"]["value"] == "capped downside and open-ended upside are supplied assumptions"
    assert "correct" not in str(result).lower()


def test_missing_or_zero_downside_makes_asymmetry_ratios_unavailable() -> None:
    values = _scenarios()
    for item in values["scenarios"]:
        item["payoff"] = abs(item["payoff"])
        item["return"] = abs(item["return"])
    result = convexity.analyze_convexity(values)
    assert result["upside_downside_multiple"]["provenance_class"] == "unavailable"
    assert result["convexity_score"]["provenance_class"] == "unavailable"
    assert result["breakeven_probability"]["provenance_class"] == "unavailable"


def test_invalid_scenario_probabilities_are_unavailable() -> None:
    values = _scenarios()
    values["scenarios"][0]["probability"] = 0.5
    result = convexity.analyze_convexity(values)
    assert all(atom["provenance_class"] == "unavailable" for atom in result.values())
    assert result["expected_value"]["reason"] == "scenario probabilities must sum to one"
