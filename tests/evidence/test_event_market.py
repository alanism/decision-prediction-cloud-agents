from __future__ import annotations

import math

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.evidence.event_market import analyze_event_market, event_market_metrics


def _snapshot(outcomes: list[dict], **overrides) -> dict:
    value = {
        "contract_version": "nhi.event_market_snapshot.v1",
        "snapshot_id": "market_001",
        "source_type": "polymarket",
        "verification_status": "user_verified",
        "title": "Synthetic event",
        "event_domain": "economy_rates",
        "event_category": "rate_decision",
        "captured_at": "2026-07-01T00:00:00Z",
        "outcomes": outcomes,
        "total_volume": 100000.0,
        "bid_ask_available": True,
        "spread_available": True,
        "resolution_rules": "Synthetic resolution rule.",
    }
    value.update(overrides)
    return value


def test_general_event_market_metrics() -> None:
    metrics = event_market_metrics(_snapshot([
        {"name": "A", "probability": 0.6, "volume": 60000},
        {"name": "B", "probability": 0.4, "volume": 40000},
    ]))
    assert metrics["consensus_score"] == 0.6
    assert metrics["surprise_probability"] == 0.4
    assert metrics["top_two_gap"] == pytest_approx(0.2)
    expected_entropy = -(0.6 * math.log(0.6) + 0.4 * math.log(0.4)) / math.log(2)
    assert metrics["normalized_entropy"] == pytest_approx(expected_entropy)


def test_volatility_and_liquidity_are_conservative() -> None:
    split = event_market_metrics(_snapshot([
        {"name": "A", "probability": 0.51}, {"name": "B", "probability": 0.49}
    ], total_volume=50.0, bid_ask_available=False, spread_available=False))
    decisive = event_market_metrics(_snapshot([
        {"name": "A", "probability": 0.95, "volume": 95000},
        {"name": "B", "probability": 0.05, "volume": 5000},
    ]))
    assert split["event_volatility_score"] > decisive["event_volatility_score"]
    assert split["market_volume_confidence"] < decisive["market_volume_confidence"]


def test_near_event_date_increases_volatility() -> None:
    outcomes = [{"name": "A", "probability": 0.7}, {"name": "B", "probability": 0.3}]
    near = event_market_metrics(_snapshot(outcomes, event_date="2026-07-02T00:00:00Z"))
    far = event_market_metrics(_snapshot(outcomes, event_date="2027-07-01T00:00:00Z"))
    assert near["event_volatility_score"] > far["event_volatility_score"]


def test_rate_domain_metrics() -> None:
    signal = analyze_event_market(_snapshot([
        {"name": "Cut", "probability": 0.5, "rate_change_bps": -25},
        {"name": "Hold", "probability": 0.3, "rate_change_bps": 0},
        {"name": "Hike", "probability": 0.2, "rate_change_bps": 25},
    ]))
    data = signal["data"]
    assert data["probability_any_cut"]["value"] == 0.5
    assert data["probability_no_change"]["value"] == 0.3
    assert data["probability_any_hike"]["value"] == 0.2
    assert data["expected_bps_change"]["value"] == pytest_approx(-7.5)
    assert data["consensus_score"]["provenance_class"] == "calculated"


def test_domain_specific_tags_and_leadership() -> None:
    geo = analyze_event_market(_snapshot([
        {"name": "Disrupted", "probability": 0.7, "tags": ["disruption", "oil_shock"]},
        {"name": "Normal", "probability": 0.3, "tags": ["normalization"]},
    ], event_domain="geopolitics", event_category="shipping_disruption"))
    assert geo["data"]["disruption_probability"]["value"] == 0.7
    tech = analyze_event_market(_snapshot([
        {"name": "Actor A", "actor": "Actor A", "probability": 0.65},
        {"name": "Actor B", "actor": "Actor B", "probability": 0.35},
    ], event_domain="technology", event_category="actor_leadership"))
    assert tech["data"]["technology_leadership_concentration"]["value"] == 0.65
    commodity = analyze_event_market(_snapshot([
        {"name": "Above", "threshold_direction": "above", "probability": 0.55},
        {"name": "Below", "threshold_direction": "below", "probability": 0.45},
    ], event_domain="commodities", event_category="price_threshold"))
    assert commodity["data"]["probability_above_threshold"]["value"] == 0.55
    structure = analyze_event_market(_snapshot([
        {"name": "Company A", "actor": "Company A", "probability": 0.8},
        {"name": "Company B", "actor": "Company B", "probability": 0.2},
    ], event_domain="market_structure", event_category="company_leadership"))
    assert structure["data"]["top_company_concentration"]["value"] == 0.8


def test_unverified_snapshot_is_not_update_eligible() -> None:
    signal = analyze_event_market(_snapshot([
        {"name": "Yes", "probability": 0.7}, {"name": "No", "probability": 0.3}
    ], verification_status="unverified_extraction"))
    assert signal["update_eligible"] is False
    assert signal["issues"] == [{"code": "EVIDENCE_NOT_VERIFIED"}]


def test_generated_signal_is_a_valid_contract() -> None:
    signal = analyze_event_market(_snapshot([
        {"name": "Yes", "probability": 0.7}, {"name": "No", "probability": 0.3}
    ]))
    assert validate_contract(signal) == []


def pytest_approx(value: float):
    import pytest
    return pytest.approx(value)
