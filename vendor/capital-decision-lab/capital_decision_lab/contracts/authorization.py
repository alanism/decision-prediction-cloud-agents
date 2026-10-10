"""Validation of separately authored, hash-bound human authorization."""

from __future__ import annotations

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract


def _issue(code: str, path: str) -> dict[str, str]:
    return {"code": code, "path": path}


def validate_binding(proposal: dict, analysis: dict, authorization: dict) -> list[dict[str, str]]:
    """Validate identity and hash bindings without creating or applying a decision."""
    if validate_contract(proposal):
        return [_issue("PROPOSAL_CONTRACT_INVALID", "$.proposal")]
    if proposal.get("canonical_hash") != contract_payload_hash(proposal):
        return [_issue("PROPOSAL_HASH_INVALID", "$.proposal.canonical_hash")]
    if validate_contract(analysis):
        return [_issue("ANALYSIS_CONTRACT_INVALID", "$.analysis")]
    if analysis.get("canonical_hash") != contract_payload_hash(analysis):
        return [_issue("ANALYSIS_HASH_INVALID", "$.analysis.canonical_hash")]
    if validate_contract(authorization):
        return [_issue("AUTHORIZATION_CONTRACT_INVALID", "$.authorization")]
    if authorization.get("canonical_hash") != contract_payload_hash(authorization):
        return [_issue("AUTHORIZATION_HASH_INVALID", "$.authorization.canonical_hash")]

    issues: list[dict[str, str]] = []
    proposal_analysis = proposal["analysis_ref"]
    if (
        proposal_analysis.get("analysis_id") != analysis.get("analysis_id")
        or proposal_analysis.get("canonical_hash") != analysis.get("canonical_hash")
    ):
        issues.append(_issue("PROPOSAL_ANALYSIS_MISMATCH", "$.proposal.analysis_ref"))
    proposal_ref = authorization["proposal_ref"]
    if (
        proposal_ref.get("proposal_id") != proposal.get("proposal_id")
        or proposal_ref.get("canonical_hash") != proposal.get("canonical_hash")
    ):
        issues.append(_issue("AUTHORIZATION_PROPOSAL_MISMATCH", "$.authorization.proposal_ref"))
    analysis_ref = authorization["analysis_ref"]
    if (
        analysis_ref.get("analysis_id") != analysis.get("analysis_id")
        or analysis_ref.get("canonical_hash") != analysis.get("canonical_hash")
    ):
        issues.append(_issue("AUTHORIZATION_ANALYSIS_MISMATCH", "$.authorization.analysis_ref"))
    return issues
