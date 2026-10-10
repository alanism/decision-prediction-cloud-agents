from __future__ import annotations

from pathlib import Path

from capital_decision_lab.ensemble.compiler import compile_claim_ensemble

ROOT = Path(__file__).resolve().parents[2]


def test_aggregation_two_family_minimum_enforcement() -> None:
    # 5 models from the SAME family (e.g. power_law with different xmin) supporting positive
    claims = [
        {
            "claim_id": "breakout_growth",
            "model_family": "power_law",
            "model_id": f"power_law_{i}",
            "direction": "positive",
            "receipt_hash": f"{i}" * 64,
        }
        for i in range(1, 6)
    ]

    res = compile_claim_ensemble(claims)
    # Since only 1 distinct model family is present, cannot be robust_positive!
    assert "breakout_growth" not in res["claims"]["robust_positive"]
    assert "breakout_growth" in res["claims"]["conditional"]


def test_aggregation_supermajority_threshold_rule() -> None:
    # 4 distinct families: power_law, markov, bass, bandit
    # required threshold = max(2, ceil(2 * 4 / 3)) = max(2, 3) = 3
    # Case A: 3 positive, 1 negative -> robust_positive
    claims_a = [
        {"claim_id": "regime_shift", "model_family": "power_law", "direction": "positive", "receipt_hash": "1" * 64},
        {"claim_id": "regime_shift", "model_family": "markov", "direction": "positive", "receipt_hash": "2" * 64},
        {"claim_id": "regime_shift", "model_family": "bass", "direction": "positive", "receipt_hash": "3" * 64},
        {"claim_id": "regime_shift", "model_family": "bandit", "direction": "negative", "receipt_hash": "4" * 64},
    ]
    res_a = compile_claim_ensemble(claims_a)
    assert "regime_shift" in res_a["claims"]["robust_positive"]

    # Case B: 2 positive, 2 negative -> not supermajority -> disputed
    claims_b = [
        {"claim_id": "regime_shift", "model_family": "power_law", "direction": "positive", "receipt_hash": "1" * 64},
        {"claim_id": "regime_shift", "model_family": "markov", "direction": "positive", "receipt_hash": "2" * 64},
        {"claim_id": "regime_shift", "model_family": "bass", "direction": "negative", "receipt_hash": "3" * 64},
        {"claim_id": "regime_shift", "model_family": "bandit", "direction": "negative", "receipt_hash": "4" * 64},
    ]
    res_b = compile_claim_ensemble(claims_b)
    assert "regime_shift" not in res_b["claims"]["robust_positive"]
    assert "regime_shift" in res_b["claims"]["disputed"]


def test_aggregation_correlated_group_collapse() -> None:
    # 3 claims from 2 distinct families, but 2 models share the same correlation group "momentum_cluster"
    claims = [
        {"claim_id": "trend", "model_family": "power_law", "direction": "positive", "receipt_hash": "1" * 64, "correlation_group": "momentum_cluster"},
        {"claim_id": "trend", "model_family": "markov", "direction": "positive", "receipt_hash": "2" * 64, "correlation_group": "momentum_cluster"},
        {"claim_id": "trend", "model_family": "bass", "direction": "positive", "receipt_hash": "3" * 64, "correlation_group": "adoption_cluster"},
    ]
    res = compile_claim_ensemble(claims)
    # momentum_cluster collapses to 1 vote + adoption_cluster 1 vote = 2 independent votes
    # Total independent groups = 2, threshold = max(2, ceil(2*2/3)) = 2. Both agree -> robust_positive
    assert "trend" in res["claims"]["robust_positive"]
    assert "momentum_cluster" in str(res["correlated_models"])


def test_aggregation_binding_veto_precedence() -> None:
    claims = [
        {"claim_id": "uptrend", "model_family": "power_law", "direction": "positive", "receipt_hash": "1" * 64},
        {"claim_id": "uptrend", "model_family": "markov", "direction": "positive", "receipt_hash": "2" * 64},
    ]
    # Supply a binding veto
    res = compile_claim_ensemble(claims, binding_vetoes=["HEAVY_TAIL_UNDEFINED_MEAN"])
    assert "HEAVY_TAIL_UNDEFINED_MEAN" in res["binding_vetoes"]
    # Binding veto suppresses robust_positive
    assert "uptrend" not in res["claims"]["robust_positive"]
    assert "uptrend" in res["claims"]["conditional"]
