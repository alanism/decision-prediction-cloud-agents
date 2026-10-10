from __future__ import annotations

import pytest
from pathlib import Path

from capital_decision_lab.ensemble.compiler import compile_claim_ensemble

ROOT = Path(__file__).resolve().parents[2]


def test_ensemble_rejects_missing_required_claim_fields() -> None:
    # Missing receipt_hash
    claims_missing_hash = [
        {"claim_id": "trend", "model_family": "power_law", "direction": "positive"}
    ]
    with pytest.raises(ValueError, match="claim record missing required fields"):
        compile_claim_ensemble(claims_missing_hash)

    # Missing claim_id
    claims_missing_id = [
        {"model_family": "power_law", "direction": "positive", "receipt_hash": "a" * 64}
    ]
    with pytest.raises(ValueError, match="claim record missing required fields"):
        compile_claim_ensemble(claims_missing_id)


def test_ensemble_rejects_invalid_direction() -> None:
    claims = [
        {
            "claim_id": "trend",
            "model_family": "power_law",
            "direction": "bullish_moon",  # invalid direction enum
            "receipt_hash": "a" * 64,
        }
    ]
    with pytest.raises(ValueError, match="invalid claim direction"):
        compile_claim_ensemble(claims)


def test_ensemble_rejects_invalid_receipt_hash_format() -> None:
    claims = [
        {
            "claim_id": "trend",
            "model_family": "power_law",
            "direction": "positive",
            "receipt_hash": "invalid_short_hash",
        }
    ]
    with pytest.raises(ValueError, match="receipt_hash must be a 64-character hex string"):
        compile_claim_ensemble(claims)


def test_ensemble_rejects_empty_claims_list() -> None:
    with pytest.raises(ValueError, match="claims list cannot be empty"):
        compile_claim_ensemble([])


def test_ensemble_rejects_hostile_or_oversized_claim_identifiers() -> None:
    # 2000-character claim_id
    claims = [
        {
            "claim_id": "x" * 2000,
            "model_family": "power_law",
            "direction": "positive",
            "receipt_hash": "a" * 64,
        }
    ]
    with pytest.raises(ValueError, match="claim identifier exceeds maximum length"):
        compile_claim_ensemble(claims)
