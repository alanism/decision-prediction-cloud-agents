from __future__ import annotations

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.evidence.social import analyze_social
from capital_decision_lab.evidence.synthesis import synthesize_evidence


def _item(source: str, item_id: str, direction: str, **extra) -> dict:
    value = {
        "item_id": item_id,
        "source_type": source,
        "verification_status": "user_verified",
        "timestamp": "2026-06-30T00:00:00Z",
        "captured_at": "2026-07-01T00:00:00Z",
        "direction": direction,
        "claim_tags": [item_id],
        "thesis_relevance": 0.8,
        "source_credibility": 0.8,
    }
    value.update(extra)
    return value


def _batch(source: str, items: list[dict], status: str = "user_verified") -> dict:
    return {
        "contract_version": "nhi.evidence_batch.v1", "batch_id": f"{source}_batch",
        "source_type": source, "verification_status": status, "items": items,
    }


def test_x_twitter_metrics_and_quality_discount() -> None:
    strong = analyze_social(_batch("x_twitter", [
        _item("x_twitter", "claim_a", "bullish", author_handle="a", likes=100, reposts=20),
        _item("x_twitter", "claim_b", "bearish", author_handle="b", likes=10),
        _item("x_twitter", "claim_a_copy", "bullish", author_handle="c", likes=50, claim_tags=["claim_a"]),
    ]))
    data = strong["data"]
    assert data["evidence_item_count"]["value"] == 3
    assert data["bullish_ratio"]["value"] == pytest_approx(2 / 3)
    assert data["bearish_ratio"]["value"] == pytest_approx(1 / 3)
    assert data["source_diversity_score"]["value"] == 1.0
    assert data["duplicate_claim_count"]["value"] == 1
    assert data["engagement_weighted_directional_score"]["value"] > 0
    weak = analyze_social(_batch("x_twitter", [
        _item("x_twitter", "weak", "bullish", author_handle="z", source_credibility=0.1)
    ]))
    assert weak["data"]["evidence_weight"]["value"] < strong["data"]["evidence_weight"]["value"]


def test_reddit_metrics() -> None:
    signal = analyze_social(_batch("reddit", [
        _item("reddit", "one", "bullish", subreddit="alpha", score=100, echo_chamber_risk=0.2),
        _item("reddit", "two", "bearish", subreddit="beta", score=50, echo_chamber_risk=0.8),
    ]))
    data = signal["data"]
    assert data["subreddit_diversity_score"]["value"] == 1.0
    assert data["upvote_weighted_directional_score"]["value"] == pytest_approx(1 / 3)
    assert data["disagreement_score"]["value"] == 1.0
    assert data["echo_chamber_risk_score"]["value"] == pytest_approx(0.5)


def test_unverified_batch_cannot_influence_updates() -> None:
    signal = analyze_social(_batch("reddit", [_item("reddit", "one", "bullish")], "unverified_extraction"))
    assert signal["update_eligible"] is False
    assert signal["data"]["evidence_weight"]["value"] == 0.0


def test_generated_social_signal_is_a_valid_contract() -> None:
    signal = analyze_social(_batch("reddit", [_item("reddit", "one", "bullish", subreddit="alpha", score=2)]))
    assert validate_contract(signal) == []


def test_synthesis_preserves_direction_volatility_and_crowding() -> None:
    event = {"source_type": "polymarket", "event_domain": "technology", "event_category": "release", "impact_channels": ["narrative_momentum"], "update_eligible": True, "data": {
        "bullish_pressure": atom(0.8), "bearish_pressure": atom(0.1), "event_volatility_score": atom(0.4), "market_volume_confidence": atom(0.9)
    }}
    social = {"source_type": "x_twitter", "event_domain": "technology", "event_category": "release", "impact_channels": ["narrative_momentum"], "update_eligible": True, "data": {
        "bullish_pressure": atom(0.7), "bearish_pressure": atom(0.2), "crowding_risk_score": atom(0.8), "evidence_weight": atom(0.7)
    }}
    result = synthesize_evidence([event, social])
    assert result["data"]["bullish_pressure"]["value"] > result["data"]["bearish_pressure"]["value"]
    assert result["data"]["volatility_pressure"]["value"] == 0.4
    assert result["data"]["crowding_pressure"]["value"] == 0.8
    assert result["data"]["source_diversity"]["value"] == 1.0
    contradictory = synthesize_evidence([event, {**social, "data": {**social["data"], "bullish_pressure": atom(0.1), "bearish_pressure": atom(0.9)}}])
    assert contradictory["data"]["contradiction_score"]["value"] > result["data"]["contradiction_score"]["value"]


def atom(value):
    return {"value": value, "provenance_class": "calculated"}


def pytest_approx(value: float):
    import pytest
    return pytest.approx(value)
