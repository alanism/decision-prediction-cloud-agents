from __future__ import annotations

import copy

from capital_decision_lab.evidence.bayesian import bayesian_probability, build_belief_update
from capital_decision_lab.evidence.proposals import apply_approved_proposal, create_assumption_proposal
from capital_decision_lab.evidence.sensitivity import match_sensitivity


def _sensitivity(direction: str = "bullish") -> dict:
    return {
        "contract_version": "nhi.thesis_sensitivity_map.v1", "map_id": "map_1",
        "target_asset": {"ticker": "SYNTH"}, "canonical_hash": "a" * 64,
        "sensitivity_rules": [{
            "source_type": "polymarket", "event_domain": "geopolitics",
            "event_category": "shipping_disruption", "impact_channel": "oil_shock",
            "direction_for_thesis": direction, "sensitivity": "high",
            "affected_assumption": "win_probability",
        }],
    }


def _synthesis() -> dict:
    return {
        "contract_version": "nhi.evidence_synthesis.v1", "canonical_hash": "b" * 64,
        "source_contexts": [{"source_type": "polymarket", "event_domain": "geopolitics", "event_category": "shipping_disruption", "impact_channels": ["oil_shock"]}],
        "evidence_refs": ["market_1"], "data": {
            "bullish_pressure": atom(0.8), "bearish_pressure": atom(0.2),
            "evidence_weight": atom(0.8), "confidence": atom(0.8),
        },
    }


def _belief() -> dict:
    return {"contract_version": "nhi.belief_state.v1", "belief_id": "belief_1", "case_ref": "case_1", "assumption": "win_probability", "prior_probability": 0.4, "canonical_hash": "c" * 64}


def test_bayesian_odds_bounds_and_cap() -> None:
    assert bayesian_probability(0.4, 1.5) == pytest_approx(0.5)
    assert bayesian_probability(0.4, 999, likelihood_bounds=(0.5, 2.0), maximum_update=0.05) == pytest_approx(0.45)
    assert 0 < bayesian_probability(0.001, 0.01) < 1


def test_sensitivity_controls_direction_without_universal_mapping() -> None:
    bull = match_sensitivity(_synthesis(), _sensitivity("bullish"))
    bear = match_sensitivity(_synthesis(), _sensitivity("bearish"))
    assert bull["direction_for_thesis"] == "bullish"
    assert bear["direction_for_thesis"] == "bearish"
    unknown = match_sensitivity(_synthesis(), {**_sensitivity(), "sensitivity_rules": []})
    assert unknown["matched"] is False


def test_belief_update_and_pending_proposal_do_not_overwrite() -> None:
    update = build_belief_update(_belief(), _synthesis(), _sensitivity())
    assert update["data"]["posterior_probability"]["value"] > 0.4
    assert update["data"]["posterior_probability"]["provenance_class"] == "forecast"
    proposal = create_assumption_proposal(update)
    assert proposal["approval_status"] == "pending"
    case = {"inputs": {"win_probability": {"value": 0.4, "provenance_class": "assumed"}}}
    assert apply_approved_proposal(case, proposal) == case
    rejected = {**proposal, "approval_status": "rejected"}
    assert apply_approved_proposal(case, rejected) == case
    approved = {**proposal, "approval_status": "approved"}
    changed = apply_approved_proposal(case, approved)
    assert changed["inputs"]["win_probability"]["value"] == update["data"]["posterior_probability"]["value"]
    assert case["inputs"]["win_probability"]["value"] == 0.4


def test_volatility_mapping_does_not_force_bull_probability() -> None:
    sensitivity = _sensitivity("volatility_increasing")
    sensitivity["sensitivity_rules"][0]["affected_assumption"] = "volatility_assumption"
    update = build_belief_update(_belief(), _synthesis(), sensitivity)
    assert update["data"]["posterior_probability"]["value"] == 0.4
    assert update["data"]["affected_assumption"]["value"] == "volatility_assumption"


def test_event_strength_takes_direction_only_from_sensitivity_map() -> None:
    synthesis = _synthesis()
    synthesis["data"]["bullish_pressure"] = atom(0.0)
    synthesis["data"]["bearish_pressure"] = atom(0.0)
    synthesis["data"]["event_evidence_strength"] = atom(0.7)
    bull = build_belief_update(_belief(), synthesis, _sensitivity("bullish"))
    bear = build_belief_update(_belief(), synthesis, _sensitivity("bearish"))
    assert bull["data"]["posterior_probability"]["value"] > 0.4
    assert bear["data"]["posterior_probability"]["value"] < 0.4


def atom(value):
    return {"value": value, "provenance_class": "calculated"}


def pytest_approx(value: float):
    import pytest
    return pytest.approx(value)
