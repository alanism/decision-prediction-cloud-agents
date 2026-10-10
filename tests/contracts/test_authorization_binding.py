from __future__ import annotations

import copy
import json
from pathlib import Path

from capital_decision_lab.contracts import authorization
from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.orchestration.analyze import analyze_case


ROOT = Path(__file__).resolve().parents[2]


def _documents() -> tuple[dict, dict, dict]:
    case = json.loads((ROOT / "fixtures" / "valid" / "mvp-case.json").read_text(encoding="utf-8"))
    analysis = analyze_case(case, alternative_id="alt_a")
    proposal = {
        "contract_version": "nhi.decision_proposal.v1",
        "proposal_id": "proposal_mvp_001",
        "analysis_ref": {
            "analysis_id": analysis["analysis_id"],
            "canonical_hash": analysis["canonical_hash"],
        },
        "selected_action": {
            "value": {"alternative_id": "alt_a", "exposure": 0.05},
            "provenance_class": "decided",
            "input_refs": [analysis["analysis_id"]],
        },
    }
    proposal["canonical_hash"] = contract_payload_hash(proposal)
    authorization_document = {
        "contract_version": "nhi.decision_authorization.v1",
        "authorization_id": "authorization_mvp_001",
        "proposal_ref": {
            "proposal_id": proposal["proposal_id"],
            "canonical_hash": proposal["canonical_hash"],
            "document_path": "../proposals/proposal_mvp_001.json",
        },
        "analysis_ref": {
            "analysis_id": analysis["analysis_id"],
            "canonical_hash": analysis["canonical_hash"],
        },
        "confirmed_by_human": True,
    }
    authorization_document["canonical_hash"] = contract_payload_hash(authorization_document)
    return proposal, analysis, authorization_document


def test_valid_hash_bound_authorization_passes() -> None:
    proposal, analysis, authorization_document = _documents()
    assert validate_contract(proposal) == []
    assert validate_contract(authorization_document) == []
    assert authorization.validate_binding(proposal, analysis, authorization_document) == []


def test_authorization_mismatch_is_rejected() -> None:
    proposal, analysis, authorization_document = _documents()
    authorization_document["analysis_ref"]["canonical_hash"] = "f" * 64
    authorization_document["canonical_hash"] = contract_payload_hash(authorization_document)
    issues = authorization.validate_binding(proposal, analysis, authorization_document)
    assert {item["code"] for item in issues} == {"AUTHORIZATION_ANALYSIS_MISMATCH"}


def test_tampered_proposal_is_rejected() -> None:
    proposal, analysis, authorization_document = _documents()
    tampered = copy.deepcopy(proposal)
    tampered["selected_action"]["value"]["exposure"] = 0.25
    issues = authorization.validate_binding(tampered, analysis, authorization_document)
    assert {item["code"] for item in issues} == {"PROPOSAL_HASH_INVALID"}


def test_validation_module_does_not_create_documents() -> None:
    assert not hasattr(authorization, "create_proposal")
    assert not hasattr(authorization, "create_authorization")
