from __future__ import annotations

import json
from pathlib import Path

import pytest

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract, validate_evidence_atom
from capital_decision_lab.orchestration import analyze, compare


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "fixtures" / "valid" / "mvp-case.json"


def _case() -> dict:
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


def test_analysis_emits_every_required_metric_as_evidence_atom() -> None:
    result = analyze.analyze_case(_case(), alternative_id="alt_a")
    required = {
        "absolute_gain_loss", "roi", "cagr", "expected_value", "expected_return",
        "volatility", "downside_deviation", "maximum_drawdown", "loss_probability",
        "value_at_risk", "expected_shortfall", "correlation", "sharpe", "sortino",
        "calmar", "return_to_drawdown", "kelly", "fractional_kelly",
        "capped_fractional_kelly", "scenario_bull", "scenario_base", "scenario_bear",
        "scenario_expected_return", "terminal_p05", "terminal_p50", "terminal_p95",
        "terminal_mean", "simulation_loss_probability",
    }
    assert required <= set(result["data"])
    assert all(validate_evidence_atom(atom) == [] for atom in result["data"].values())
    assert result["data"]["roi"]["value"] == pytest.approx(0.1)
    assert result["data"]["capped_fractional_kelly"]["value"] == pytest.approx(0.05)
    assert result["alternative_id"] == "alt_a"
    assert result["case_ref"]["canonical_hash"] == contract_payload_hash(_case())
    assert validate_contract(result) == []


def test_analysis_is_deterministic_for_same_case_and_seed() -> None:
    assert analyze.analyze_case(_case(), alternative_id="alt_a") == analyze.analyze_case(
        _case(), alternative_id="alt_a"
    )


def test_missing_inputs_produce_unavailable_atoms() -> None:
    case = _case()
    case["inputs"] = {}
    case["alternatives"] = [{"alternative_id": "empty", "label": "Empty", "inputs": {}}]
    result = analyze.analyze_case(case, alternative_id="empty")
    assert set(result["data"])
    assert all(atom["provenance_class"] == "unavailable" for atom in result["data"].values())
    assert all(atom["reason"] for atom in result["data"].values())


def test_comparison_is_unranked_and_schema_valid() -> None:
    result = compare.compare_case(_case())
    document = result["comparison"]
    assert len(result["analyses"]) == 2
    assert set(document["data"]) == set(result["analyses"][0]["data"])
    assert all(validate_evidence_atom(atom) == [] for atom in document["data"].values())
    assert "ranking" not in document
    assert "selected_alternative" not in document
    assert document["disclaimer"] == "comparison only, not financial advice"
    assert validate_contract(document) == []
