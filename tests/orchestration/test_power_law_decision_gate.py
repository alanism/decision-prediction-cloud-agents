from __future__ import annotations

import copy
from pathlib import Path

from capital_decision_lab.calculations.power_law import fit_power_law_tail
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.recommendation.engine import build_recommendation

ROOT = Path(__file__).resolve().parents[2]

SIX_STRING_VOCABULARY = {
    "pause",
    "hold",
    "avoid_margin",
    "decrease_exposure",
    "watch",
    "increase_exposure",
    "trim_to_kelly",
}


def base_recommendation_inputs() -> dict:
    """Generate valid base recommendation inputs proposing exposure increase."""
    return {
        "case_id": "case_power_law_gate_001",
        "current_exposure": 0.20,
        "kelly_implied_exposure": 0.45,
        "fractional_kelly": 0.40,
        "exposure_cap": 0.50,
        "convexity_score": 0.80,
        "evidence_quality": 0.90,
        "evidence_contradiction": 0.0,
        "belief_update_status": "approved",
        "model_health": {
            "state": "healthy",
            "canonical_hash": "a" * 64,
        },
        "portfolio": {
            "verification_status": "user_verified",
            "positions": [
                {
                    "ticker": "SEMI",
                    "shares": 100,
                    "current_price": 50,
                    "market_value": 5000,
                    "user_intent": "grow",
                    "max_position_cap": 0.50,
                }
            ],
        },
        "host_extractions": [],
        "margin_breach": False,
        "margin_buffer": 0.40,
        "hashes": {
            "portfolio_snapshot": "1" * 64,
            "belief_state": "2" * 64,
            "evidence_synthesis": "3" * 64,
            "kelly_analysis": "4" * 64,
            "convexity_analysis": "5" * 64,
            "margin_analysis": "6" * 64,
        },
    }


def test_heavy_tail_undefined_mean_blocks_positive_exposure_change() -> None:
    # alpha <= 2.0 (undefined mean)
    # Synthetic samples with alpha ~ 1.8
    obs = [10.0 * (1.0 + i * 0.2) for i in range(100)]
    power_law_res = fit_power_law_tail(obs, 10.0, bootstrap_trials=50, seed=42)
    # Override alpha atom to simulate verified alpha = 1.8 <= 2.0
    power_law_res["data"]["alpha"]["value"] = 1.8
    power_law_res["data"]["mean_defined"]["value"] = False
    power_law_res["data"]["variance_defined"]["value"] = False

    inputs = base_recommendation_inputs()
    inputs["power_law_result"] = power_law_res

    rec = build_recommendation(inputs)
    assert rec["recommendation_type"] in SIX_STRING_VOCABULARY
    assert rec["recommendation_type"] != "increase_exposure"
    assert rec["recommendation_type"] in {"watch", "hold"}
    assert rec["target_exposure"]["value"] == inputs["current_exposure"]
    assert "HEAVY_TAIL_UNDEFINED_MEAN" in rec["reason_codes"]


def test_heavy_tail_unavailable_fit_blocks_positive_exposure_change() -> None:
    # Unavailable fit
    obs = [10.0 for _ in range(40)]  # Undersized
    power_law_res = fit_power_law_tail(obs, 10.0)

    inputs = base_recommendation_inputs()
    inputs["power_law_result"] = power_law_res

    rec = build_recommendation(inputs)
    assert rec["recommendation_type"] in SIX_STRING_VOCABULARY
    assert rec["recommendation_type"] != "increase_exposure"
    assert rec["target_exposure"]["value"] == inputs["current_exposure"]
    assert "HEAVY_TAIL_FIT_UNAVAILABLE" in rec["reason_codes"]


def test_heavy_tail_infinite_variance_allows_kelly_sizing() -> None:
    # 2.0 < alpha <= 3.0 (defined mean, infinite variance)
    obs = [10.0 * (1.0 + i * 0.1) for i in range(100)]
    power_law_res = fit_power_law_tail(obs, 10.0, bootstrap_trials=50, seed=42)
    power_law_res["data"]["alpha"]["value"] = 2.5
    power_law_res["data"]["mean_defined"]["value"] = True
    power_law_res["data"]["variance_defined"]["value"] = False

    inputs = base_recommendation_inputs()
    inputs["power_law_result"] = power_law_res

    rec = build_recommendation(inputs)
    assert rec["recommendation_type"] in SIX_STRING_VOCABULARY
    assert rec["recommendation_type"] == "increase_exposure"
    assert rec["target_exposure"]["value"] == 0.40  # fractional kelly limit
    assert "HEAVY_TAIL_INFINITE_VARIANCE_ALLOWED" in rec["reason_codes"]


def test_margin_danger_always_overrides_heavy_tail() -> None:
    # Even if alpha is healthy, margin danger MUST trigger avoid_margin
    obs = [10.0 * (1.0 + i * 0.1) for i in range(100)]
    power_law_res = fit_power_law_tail(obs, 10.0, bootstrap_trials=50, seed=42)
    power_law_res["data"]["alpha"]["value"] = 3.5
    power_law_res["data"]["mean_defined"]["value"] = True
    power_law_res["data"]["variance_defined"]["value"] = True

    inputs = base_recommendation_inputs()
    inputs["margin_breach"] = True
    inputs["margin_buffer"] = -0.10
    inputs["power_law_result"] = power_law_res

    rec = build_recommendation(inputs)
    assert rec["recommendation_type"] == "avoid_margin"
    assert "MARGIN_OVERRIDE" in rec["reason_codes"]


def test_recommendation_output_strict_schema_and_vocabulary() -> None:
    inputs = base_recommendation_inputs()
    rec = build_recommendation(inputs)
    assert rec["recommendation_type"] in SIX_STRING_VOCABULARY
    issues = validate_contract(rec)
    assert not issues, f"Contract validation failed: {issues}"
