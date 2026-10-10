from __future__ import annotations

import hashlib
from pathlib import Path

from capital_decision_lab.contracts import validation as contracts
from capital_decision_lab.evidence import validation


def _item(source_type: str = "polymarket", status: str = "user_verified") -> dict:
    return {
        "contract_version": "nhi.evidence_item.v1",
        "item_id": "evidence_item_001",
        "source_ref": "source_001",
        "source_type": source_type,
        "verification_status": status,
        "timestamp": "2026-07-01T00:00:00Z",
        "captured_at": "2026-07-01T01:00:00Z",
        "direction": "bullish",
        "claim_tags": ["synthetic_claim"],
        "content": {"text": "Synthetic evidence"},
        "thesis_relevance": 0.8,
        "source_credibility": 0.7,
    }


def test_forecast_is_a_first_class_provenance_atom() -> None:
    atom = {
        "value": 0.37,
        "provenance_class": "forecast",
        "unit": "probability",
        "input_refs": ["belief_prior", "evidence_synthesis"],
        "limitations": ["Forward-looking estimate under supplied assumptions"],
    }
    assert contracts.validate_evidence_atom(atom) == []


def test_evidence_contract_schemas_load() -> None:
    versions = {
        "nhi.evidence_source.v1",
        "nhi.evidence_item.v1",
        "nhi.evidence_batch.v1",
        "nhi.event_market_snapshot.v1",
        "nhi.event_market_signal.v1",
        "nhi.social_evidence_signal.v1",
        "nhi.thesis_sensitivity_map.v1",
        "nhi.belief_state.v1",
        "nhi.bayesian_update.v1",
        "nhi.assumption_update_proposal.v1",
    }
    assert versions <= set(contracts.supported_contract_versions())
    for version in versions:
        assert contracts.load_schema(version)["properties"]["contract_version"]["const"] == version


def test_valid_source_item_and_batch_validate() -> None:
    source = {
        "contract_version": "nhi.evidence_source.v1",
        "source_id": "source_001",
        "source_type": "polymarket",
        "captured_at": "2026-07-01T01:00:00Z",
        "verification_status": "user_verified",
        "artifact_refs": [],
    }
    batch = {
        "contract_version": "nhi.evidence_batch.v1",
        "batch_id": "batch_001",
        "source_type": "polymarket",
        "verification_status": "user_verified",
        "items": [_item()],
    }
    assert contracts.validate_contract(source) == []
    assert contracts.validate_contract(_item()) == []
    assert contracts.validate_contract(batch) == []


def test_invalid_source_type_and_verification_status_fail() -> None:
    invalid_source = _item(source_type="broker_api")
    invalid_status = _item(status="model_verified")
    assert "SCHEMA_ENUM_INVALID" in {item["code"] for item in contracts.validate_contract(invalid_source)}
    assert "SCHEMA_ENUM_INVALID" in {item["code"] for item in contracts.validate_contract(invalid_status)}


def test_only_verified_or_corrected_evidence_is_update_eligible() -> None:
    assert validation.update_eligibility(_item(status="auto_retrieved"))["eligible"] is True
    assert validation.update_eligibility(_item(status="user_verified"))["eligible"] is True
    assert validation.update_eligibility(_item(status="user_corrected"))["eligible"] is True
    blocked = validation.update_eligibility(_item(status="unverified_extraction"))
    assert blocked == {
        "eligible": False,
        "issues": [{"code": "EVIDENCE_NOT_VERIFIED"}],
    }


def test_local_artifact_paths_and_hashes_are_verified(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    artifact = local / "source.txt"; artifact.write_text("synthetic source", encoding="utf-8")
    source = {
        "contract_version": "nhi.evidence_source.v1", "source_id": "source_1",
        "source_type": "manual_note", "captured_at": "2026-07-01T00:00:00Z",
        "verification_status": "user_verified", "artifact_refs": [{
            "path": "source.txt", "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        }],
    }
    assert validation.validate_local_evidence(source, local) == []
    source["artifact_refs"][0]["sha256"] = "0" * 64
    assert {issue["code"] for issue in validation.validate_local_evidence(source, local)} == {"EVIDENCE_ARTIFACT_HASH_MISMATCH"}
    source["artifact_refs"][0]["path"] = "../outside.txt"
    assert "PATH_ESCAPE_FORBIDDEN" in {issue["code"] for issue in validation.validate_local_evidence(source, local)}
