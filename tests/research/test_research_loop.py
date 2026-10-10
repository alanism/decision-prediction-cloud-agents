from __future__ import annotations

from capital_decision_lab.research.loop import evaluate_research_readiness


def test_missing_kelly_and_margin_inputs_trigger_specific_loops() -> None:
    result = evaluate_research_readiness({"inputs": {}})
    codes = {item["code"] for item in result["requests"]}
    assert result["status"] == "blocked_missing_user_input"
    assert {"KELLY_INPUTS_REQUIRED", "MARGIN_INPUTS_REQUIRED"} <= codes


def test_unverified_and_contradictory_evidence_trigger_loops() -> None:
    case = {"inputs": {"win_probability": 0.6, "upside_payoff": 1.0, "downside_loss": 0.5, "capital_at_risk": 1000, "max_exposure_cap": 0.1, "maintenance_margin_requirement": 0.25, "borrowed_amount": 1000, "current_price": 100, "shares": 10}}
    unverified = evaluate_research_readiness(case, evidence={"verification_status": "unverified_extraction"})
    assert unverified["status"] == "blocked_low_confidence"
    contradiction = evaluate_research_readiness(case, evidence={"verification_status": "user_verified", "data": {"contradiction_score": {"value": 0.8}}})
    assert contradiction["status"] == "blocked_missing_user_input"
    assert contradiction["requests"][0]["code"] == "EVIDENCE_CONTRADICTION_REQUIRES_WEIGHT"


def test_complete_inputs_are_analysis_ready() -> None:
    case = {"inputs": {"win_probability": 0.6, "upside_payoff": 1.0, "downside_loss": 0.5, "capital_at_risk": 1000, "max_exposure_cap": 0.1, "maintenance_margin_requirement": 0.25, "borrowed_amount": 1000, "current_price": 100, "shares": 10}}
    assert evaluate_research_readiness(case, evidence={"verification_status": "auto_retrieved", "data": {"contradiction_score": {"value": 0.2}}})["status"] == "analysis_ready"
