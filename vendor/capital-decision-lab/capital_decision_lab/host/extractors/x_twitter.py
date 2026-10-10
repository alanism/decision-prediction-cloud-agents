"""Normalize X/Twitter host extraction into a social evidence batch."""

from __future__ import annotations

from .common import extraction_bundle, response_fields


def extract_x_twitter(response: dict) -> dict:
    fields, status = response_fields(response)
    if not fields.get("post_text"):
        raise ValueError("X_POST_TEXT_REQUIRED")
    item = {
        "item_id": f"host_item_{response['response_id']}", "source_type": "x_twitter",
        "verification_status": status, "author_handle": fields.get("author_handle"),
        "author_display_name": fields.get("author_display_name"), "post_text": fields["post_text"],
        "post_url": fields.get("post_url", response.get("source_url")),
        "timestamp": fields.get("timestamp"), "captured_at": response["retrieval_timestamp"],
        "likes": fields.get("likes"), "reposts": fields.get("reposts"), "replies": fields.get("replies"),
        "views": fields.get("views"), "quoted_source": fields.get("quoted_source"),
        "screenshot_hash": response.get("source_artifact_hash") if response.get("retrieval_method") == "screenshot" else None,
        "direction": fields.get("direction_candidate", "unknown"), "claim_tags": fields.get("claim_tags", []),
        "source_credibility": fields.get("source_credibility", 0.5), "thesis_relevance": fields.get("thesis_relevance", 0.5),
    }
    item = {name: value for name, value in item.items() if value is not None}
    document = {"contract_version": "nhi.evidence_batch.v1", "batch_id": f"host_batch_{response['response_id']}", "source_type": "x_twitter", "verification_status": status, "items": [item]}
    return extraction_bundle(response, "x_twitter", fields, document)
