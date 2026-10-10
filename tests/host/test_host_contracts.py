from __future__ import annotations

import hashlib
from pathlib import Path

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.host.artifacts import validate_host_artifact


def finalized(document: dict) -> dict:
    document["canonical_hash"] = contract_payload_hash(document)
    return document


def capability_request() -> dict:
    return finalized({
        "contract_version": "nhi.host_capability_request.v1", "request_id": "request_1",
        "capability": "browser_fetch_url", "source_type": "polymarket",
        "parameters": {"url": "https://example.invalid/market"},
    })


def test_host_capability_request_and_response_validate() -> None:
    request = capability_request()
    response = finalized({
        "contract_version": "nhi.host_capability_response.v1", "response_id": "response_1",
        "request_ref": {"request_id": request["request_id"], "canonical_hash": request["canonical_hash"]},
        "capability": "browser_fetch_url", "status": "ok", "retrieval_method": "browser",
        "retrieval_timestamp": "2026-07-04T00:00:00Z", "source_url": "https://example.invalid/market",
        "raw_content_hash": "a" * 64, "payload": {"text": "Synthetic host payload"},
        "confidence": 0.9, "limitations": [],
    })
    assert validate_contract(request) == []
    assert validate_contract(response) == []


def test_host_source_artifact_validates() -> None:
    artifact = finalized({
        "contract_version": "nhi.host_source_artifact.v1", "artifact_id": "artifact_1",
        "artifact_path": "sources/synthetic.png", "artifact_hash": "b" * 64,
        "mime_type": "image/png", "captured_at": "2026-07-04T00:00:00Z", "local_only": True,
    })
    assert validate_contract(artifact) == []


def test_host_source_artifact_must_be_local_and_hash_bound(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    source = local / "real-runtime-source.png"; source.write_bytes(b"real runtime bytes")
    artifact = finalized({"contract_version": "nhi.host_source_artifact.v1", "artifact_id": "artifact_real", "artifact_path": "real-runtime-source.png", "artifact_hash": hashlib.sha256(source.read_bytes()).hexdigest(), "mime_type": "image/png", "captured_at": "2026-07-04T00:00:00Z", "local_only": True})
    assert validate_host_artifact(artifact, local) == []
    artifact["artifact_hash"] = "0" * 64; artifact["canonical_hash"] = contract_payload_hash(artifact)
    assert {issue["code"] for issue in validate_host_artifact(artifact, local)} == {"HOST_ARTIFACT_HASH_MISMATCH"}


def test_host_extraction_and_user_confirmation_validate() -> None:
    extraction = finalized({
        "contract_version": "nhi.host_extraction_result.v1", "extraction_id": "extraction_1",
        "source_type": "x_twitter", "input_ref": {"id": "response_1", "canonical_hash": "c" * 64},
        "retrieval_method": "screenshot", "extracted_fields": {"post_text": "Synthetic post"},
        "field_confidence": {"post_text": 0.8}, "verification_status": "unverified_extraction",
        "limitations": ["Screenshot extraction requires confirmation."],
    })
    confirmation = finalized({
        "contract_version": "nhi.host_user_confirmation.v1", "confirmation_id": "confirmation_1",
        "extraction_ref": {"extraction_id": extraction["extraction_id"], "canonical_hash": extraction["canonical_hash"]},
        "action": "confirm", "corrections": {}, "confirmed_by_human": True,
    })
    assert validate_contract(extraction) == []
    assert validate_contract(confirmation) == []


def test_invalid_capability_and_status_fail() -> None:
    request = capability_request(); request["capability"] = "trade_execution"
    assert "SCHEMA_ENUM_INVALID" in {issue["code"] for issue in validate_contract(request)}
    extraction = finalized({
        "contract_version": "nhi.host_extraction_result.v1", "extraction_id": "extraction_bad",
        "source_type": "reddit", "input_ref": {"id": "response_1", "canonical_hash": "c" * 64},
        "retrieval_method": "browser", "extracted_fields": {}, "field_confidence": {},
        "verification_status": "model_verified", "limitations": [],
    })
    assert "SCHEMA_ENUM_INVALID" in {issue["code"] for issue in validate_contract(extraction)}
