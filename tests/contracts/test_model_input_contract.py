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


def valid_model_input() -> dict:
    return {
        "contract_version": "nhi.model_input.v1",
        "model_id": "power_law_tail",
        "model_family": "power_law",
        "model_version": "1.0.0",
        "input_trust_class": "synthetic_test",
        "parameters": {
            "xmin": 10.0,
            "observations": [10.5, 12.0, 15.0, 20.0, 30.0, 50.0],
        },
        "input_refs": ["test.fixture.obs"],
        "claim_specs": [
            {
                "claim_id": "heavy_tail_distribution",
                "target_property": "tail_shape",
                "direction": "supports",
            }
        ],
        "limitations": ["synthetic sample for testing"],
    }


def test_model_input_contract_registered() -> None:
    assert "nhi.model_input.v1" in supported_contract_versions()
    schema = load_schema("nhi.model_input.v1")
    assert schema["properties"]["contract_version"]["const"] == "nhi.model_input.v1"


def test_model_input_trust_classes() -> None:
    schema = load_schema("nhi.model_input.v1")
    trust_classes = schema["properties"]["input_trust_class"]["enum"]
    assert sorted(trust_classes) == [
        "synthetic_test",
        "untrusted_external",
        "user_verified",
        "verified_local",
    ]


def test_model_input_validation_success() -> None:
    doc = valid_model_input()
    doc["canonical_hash"] = contract_payload_hash(doc)
    issues = validate_contract(doc)
    assert not issues, f"Validation failed with issues: {issues}"


def test_model_input_rejects_unknown_trust_class() -> None:
    doc = valid_model_input()
    doc["input_trust_class"] = "arbitrary_untrusted"
    doc["canonical_hash"] = contract_payload_hash(doc)
    issues = validate_contract(doc)
    assert any(i["code"] == "SCHEMA_ENUM_INVALID" for i in issues)


def test_model_input_rejects_boolean_as_number() -> None:
    doc = valid_model_input()
    doc["parameters"]["xmin"] = True
    doc["canonical_hash"] = contract_payload_hash(doc)
    issues = validate_contract(doc)
    assert any(i["code"] == "SCHEMA_TYPE_INVALID" for i in issues)


def test_model_input_rejects_missing_required_fields() -> None:
    for required_key in ["model_id", "model_family", "model_version", "input_trust_class", "parameters"]:
        doc = valid_model_input()
        del doc[required_key]
        doc["canonical_hash"] = contract_payload_hash(doc)
        issues = validate_contract(doc)
        assert any(i["code"] == "SCHEMA_REQUIRED_MISSING" for i in issues)
