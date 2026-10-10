"""Hash-bound promotion or correction of host extraction results."""

from __future__ import annotations

import copy

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract


def apply_confirmation(bundle: dict, confirmation: dict) -> dict:
    extraction = bundle.get("extraction", {})
    if validate_contract(confirmation) or confirmation.get("canonical_hash") != contract_payload_hash(confirmation):
        raise ValueError("HOST_CONFIRMATION_INVALID")
    reference = confirmation["extraction_ref"]
    if reference["extraction_id"] != extraction.get("extraction_id") or reference["canonical_hash"] != extraction.get("canonical_hash"):
        raise ValueError("HOST_CONFIRMATION_MISMATCH")
    if confirmation["action"] == "reject":
        updated = copy.deepcopy(bundle); updated["extraction"]["verification_status"] = "failed"; updated["document"]["verification_status"] = "failed"
        updated["extraction"]["canonical_hash"] = contract_payload_hash(updated["extraction"]); updated["requires_confirmation"] = False
        return updated
    updated = copy.deepcopy(bundle)
    corrections = confirmation.get("corrections", {})
    updated["extraction"]["extracted_fields"].update(corrections)
    status = "user_corrected" if confirmation["action"] == "correct" else "user_verified"
    updated["extraction"]["verification_status"] = status
    document = updated["document"]
    document["verification_status"] = status
    if document.get("source_type") in {"x_twitter", "reddit", "manual_note"}:
        target = document["items"][0]
        target.update(corrections); target["verification_status"] = status
    else:
        mapping = {"market_title": "title", "resolution_date": "event_date"}
        document.update({mapping.get(name, name): value for name, value in corrections.items()})
    updated["extraction"]["canonical_hash"] = contract_payload_hash(updated["extraction"])
    updated["requires_confirmation"] = False
    return updated
