"""Normalize a real user-provided manual note."""

from __future__ import annotations

from .common import extraction_bundle, response_fields


def extract_manual_note(response: dict) -> dict:
    fields, status = response_fields(response)
    text = str(fields.get("text", "")).strip()
    if not text:
        raise ValueError("MANUAL_NOTE_TEXT_REQUIRED")
    item = {"item_id": f"host_item_{response['response_id']}", "source_type": "manual_note", "verification_status": status, "timestamp": response["retrieval_timestamp"], "captured_at": response["retrieval_timestamp"], "direction": fields.get("direction_candidate", "unknown"), "claim_tags": fields.get("claim_tags", []), "content": {"text": text}, "thesis_relevance": fields.get("thesis_relevance", 0.5), "source_credibility": fields.get("source_credibility", 1.0)}
    document = {"contract_version": "nhi.evidence_batch.v1", "batch_id": f"host_batch_{response['response_id']}", "source_type": "manual_note", "verification_status": status, "items": [item]}
    return extraction_bundle(response, "manual_note", fields, document)
