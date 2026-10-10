"""Shared validation and provenance for host extraction adapters."""

from __future__ import annotations

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract


def response_fields(response: dict) -> tuple[dict, str]:
    if validate_contract(response) or response.get("canonical_hash") != contract_payload_hash(response):
        raise ValueError("HOST_CAPABILITY_RESPONSE_INVALID")
    if response.get("status") != "ok":
        raise ValueError("HOST_CAPABILITY_RESPONSE_UNAVAILABLE")
    payload = response.get("payload", {})
    fields = payload.get("extracted_fields", payload)
    if not isinstance(fields, dict):
        raise ValueError("HOST_EXTRACTED_FIELDS_INVALID")
    return fields, verification_status(response)


def verification_status(response: dict) -> str:
    method = response.get("retrieval_method")
    confidence = float(response.get("confidence", 0.0))
    field_confidence = response.get("payload", {}).get("field_confidence", {})
    lowest_field = min((float(value) for value in field_confidence.values()), default=1.0) if isinstance(field_confidence, dict) else 0.0
    if method == "manual":
        return "user_verified"
    if method == "screenshot" or confidence < 0.7 or lowest_field < 0.7:
        return "unverified_extraction"
    return "auto_retrieved"


def extraction_bundle(response: dict, source_type: str, fields: dict, document: dict) -> dict:
    status = verification_status(response)
    confidence = float(response.get("confidence", 0.0))
    supplied_confidence = response.get("payload", {}).get("field_confidence", {})
    field_confidence = {name: float(supplied_confidence.get(name, confidence)) for name in fields} if isinstance(supplied_confidence, dict) else {name: confidence for name in fields}
    extraction = {
        "contract_version": "nhi.host_extraction_result.v1",
        "extraction_id": f"extraction_{canonical_sha256([response['response_id'], source_type])[:16]}",
        "source_type": source_type,
        "input_ref": {"id": response["response_id"], "canonical_hash": response["canonical_hash"]},
        "retrieval_method": response["retrieval_method"],
        "extracted_fields": fields,
        "field_confidence": field_confidence,
        "verification_status": status,
        "limitations": list(response.get("limitations", [])),
    }
    if response.get("source_url"):
        extraction["source_url"] = response["source_url"]
    if response.get("raw_content_hash"):
        extraction["raw_content_hash"] = response["raw_content_hash"]
    if response.get("source_artifact_hash"):
        extraction["source_artifact_hash"] = response["source_artifact_hash"]
    extraction["canonical_hash"] = contract_payload_hash(extraction)
    return {"extraction": extraction, "document": document, "requires_confirmation": status == "unverified_extraction", "issues": []}
