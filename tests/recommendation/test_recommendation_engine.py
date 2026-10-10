from __future__ import annotations

from capital_decision_lab.recommendation.engine import build_recommendation
from capital_decision_lab.contracts.validation import validate_contract
from tests.research.test_portfolio_thesis_contracts import portfolio


def inputs(**overrides):
    value = {
        "case_id": "case_1", "portfolio": portfolio(), "current_exposure": 0.2,
        "kelly_implied_exposure": 0.3, "fractional_kelly": 0.25, "exposure_cap": 0.35,
        "convexity_score": 0.7, "margin_buffer": 0.5, "margin_breach": False,
        "model_health": {"state": "healthy", "canonical_hash": "a" * 64},
        "evidence_quality": 0.8, "belief_update_status": "approved",
        "hashes": {name: char * 64 for name, char in {
            "portfolio_snapshot": "b", "belief_state": "c", "evidence_synthesis": "d",
            "kelly_analysis": "e", "convexity_analysis": "f", "margin_analysis": "1",
        }.items()},
    }
    value.update(overrides)
    return value


def test_kelly_can_increase_or_trim_exposure() -> None:
    assert build_recommendation(inputs())["recommendation_type"] == "increase_exposure"
    assert build_recommendation(inputs(current_exposure=0.4, kelly_implied_exposure=0.2))["recommendation_type"] == "trim_to_kelly"


def test_margin_danger_overrides_kelly_increase() -> None:
    result = build_recommendation(inputs(margin_breach=True, margin_buffer=-0.1))
    assert result["recommendation_type"] == "avoid_margin"
    assert "MARGIN_OVERRIDE" in result["reason_codes"]


def test_fractional_kelly_and_position_cap_bound_target() -> None:
    value = inputs(current_exposure=0.1, kelly_implied_exposure=0.4, fractional_kelly=0.3, exposure_cap=0.35)
    value["portfolio"]["positions"][0]["max_position_cap"] = 0.22
    result = build_recommendation(value)
    assert result["target_exposure"]["value"] == 0.22


def test_weak_evidence_and_degrading_health_are_conservative() -> None:
    assert build_recommendation(inputs(evidence_quality=0.2))["recommendation_type"] == "watch"
    degrading = build_recommendation(inputs(model_health={"state": "degrading", "canonical_hash": "a" * 64}))
    assert degrading["recommendation_type"] in {"decrease_exposure", "pause"}


def test_unverified_portfolio_and_pending_updates_cannot_drive_change() -> None:
    unverified = portfolio("unverified_extraction")
    assert build_recommendation(inputs(portfolio=unverified))["recommendation_type"] == "pause"
    pending = build_recommendation(inputs(belief_update_status="pending"))
    rejected = build_recommendation(inputs(belief_update_status="rejected"))
    assert pending["target_exposure"]["value"] == pending["current_exposure"]["value"]
    assert rejected["target_exposure"]["value"] == rejected["current_exposure"]["value"]


def test_recommendation_contains_hashes_and_requires_authorization() -> None:
    result = build_recommendation(inputs())
    assert result["required_user_authorization"] is True
    assert result["contract_version"] == "nhi.recommendation.v1"
    assert all(len(result[name]) == 64 for name in (
        "portfolio_snapshot_hash", "belief_state_hash", "evidence_synthesis_hash",
        "kelly_analysis_hash", "convexity_analysis_hash", "margin_analysis_hash", "model_health_hash",
    ))
    assert len(result["canonical_hash"]) == 64
    assert validate_contract(result) == []
