from __future__ import annotations

import copy
import json
from pathlib import Path

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import (
    load_schema,
    supported_contract_versions,
    validate_contract,
)

ROOT = Path(__file__).resolve().parents[2]


def valid_ensemble_result() -> dict:
    return {
        "contract_version": "nhi.ensemble_result.v1",
        "ensemble_id": "ensemble_result_001",
        "aggregated_by": "engine",
        "contributing_receipt_hashes": [
            "1111111111111111111111111111111111111111111111111111111111111111",
            "2222222222222222222222222222222222222222222222222222222222222222",
        ],
        "applicable_family_count": 2,
        "threshold_constant_version": "v1.0",
        "correlated_models": [],
        "claims": {
            "robust_positive": ["long_run_durability"],
            "conditional": [],
            "disputed": [],
        },
        "binding_vetoes": [],
        "limitations": [
            "Ensemble aggregation is deterministic over typed claims, not average of raw numbers."
        ],
    }


def test_ensemble_result_contract_registered() -> None:
    assert "nhi.ensemble_result.v1" in supported_contract_versions()
    schema = load_schema("nhi.ensemble_result.v1")
    assert schema["properties"]["contract_version"]["const"] == "nhi.ensemble_result.v1"


def test_ensemble_result_aggregated_by_engine_only() -> None:
    schema = load_schema("nhi.ensemble_result.v1")
    assert schema["properties"]["aggregated_by"]["const"] == "engine"


def test_ensemble_result_validation_success() -> None:
    doc = valid_ensemble_result()
    doc["canonical_hash"] = contract_payload_hash(doc)
    issues = validate_contract(doc)
    assert not issues, f"Validation failed with issues: {issues}"


def test_ensemble_result_rejects_non_engine_aggregator() -> None:
    doc = valid_ensemble_result()
    doc["aggregated_by"] = "llm_freehand"
    doc["canonical_hash"] = contract_payload_hash(doc)
    issues = validate_contract(doc)
    assert any(i["code"] == "SCHEMA_CONST_MISMATCH" for i in issues)


def test_ensemble_result_rejects_missing_receipt_hashes() -> None:
    doc = valid_ensemble_result()
    del doc["contributing_receipt_hashes"]
    doc["canonical_hash"] = contract_payload_hash(doc)
    issues = validate_contract(doc)
    assert any(i["code"] == "SCHEMA_REQUIRED_MISSING" for i in issues)
