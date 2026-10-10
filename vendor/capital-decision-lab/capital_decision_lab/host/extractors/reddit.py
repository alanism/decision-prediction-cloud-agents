"""Normalize Reddit host extraction into a social evidence batch."""

from __future__ import annotations

from .common import extraction_bundle, response_fields


def extract_reddit(response: dict) -> dict:
    fields, status = response_fields(response)
    if not fields.get("post_text") and not fields.get("comment_text"):
        raise ValueError("REDDIT_TEXT_REQUIRED")
    item = {
        "item_id": f"host_item_{response['response_id']}", "source_type": "reddit", "verification_status": status,
        "subreddit": fields.get("subreddit"), "thread_title": fields.get("thread_title"),
        "thread_url": fields.get("thread_url", response.get("source_url")), "post_text": fields.get("post_text"),
        "comment_text": fields.get("comment_text"), "author_name": fields.get("author"),
        "timestamp": fields.get("timestamp"), "captured_at": response["retrieval_timestamp"],
        "score": fields.get("score", fields.get("upvotes")), "comment_count": fields.get("comment_count"), "flair": fields.get("flair"),
        "direction": fields.get("direction_candidate", "unknown"), "claim_tags": fields.get("claim_tags", []),
        "echo_chamber_risk": fields.get("echo_chamber_risk", 0.5), "source_credibility": fields.get("source_credibility", 0.5),
        "thesis_relevance": fields.get("thesis_relevance", 0.5),
    }
    item = {name: value for name, value in item.items() if value is not None}
    document = {"contract_version": "nhi.evidence_batch.v1", "batch_id": f"host_batch_{response['response_id']}", "source_type": "reddit", "verification_status": status, "items": [item]}
    return extraction_bundle(response, "reddit", fields, document)
