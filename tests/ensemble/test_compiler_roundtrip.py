from __future__ import annotations

from pathlib import Path

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.ensemble.compiler import compile_claim_ensemble

ROOT = Path(__file__).resolve().parents[2]


def test_compiler_roundtrip_valid_multi_family_ensemble() -> None:
    # 3 distinct model families supporting the same claim "tail_growth"
    claims = [
        {
            "claim_id": "tail_growth",
            "model_family": "power_law",
            "model_id": "power_law_tail",
            "direction": "positive",
            "receipt_hash": "a" * 64,
        },
        {
            "claim_id": "tail_growth",
            "model_family": "markov",
            "model_id": "markov_regime",
            "direction": "positive",
            "receipt_hash": "b" * 64,
        },
        {
            "claim_id": "tail_growth",
            "model_family": "bass",
            "model_id": "bass_diffusion",
            "direction": "positive",
            "receipt_hash": "c" * 64,
        },
    ]

    res = compile_claim_ensemble(claims)

    assert res["contract_version"] == "nhi.ensemble_result.v1"
    assert res["aggregated_by"] == "engine"
    assert res["threshold_constant_version"] == "page_supermajority_v1"
    assert res["applicable_family_count"] == 3
    assert set(res["contributing_receipt_hashes"]) == {"a" * 64, "b" * 64, "c" * 64}
    assert "tail_growth" in res["claims"]["robust_positive"]
    assert res["claims"]["conditional"] == []
    assert res["claims"]["disputed"] == []
    assert res["binding_vetoes"] == []

    issues = validate_contract(res)
    assert not issues, f"Contract validation failed: {issues}"
