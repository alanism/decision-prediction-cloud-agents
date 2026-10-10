"""Hash-bound confirmation queues and deterministic response pairing."""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash
from capital_decision_lab.host.confirmation import apply_confirmation


ACTIONS = ["confirm", "correct", "discard", "defer"]


def _valid(document: dict, version: str, required: set[str]) -> bool:
    return (
        isinstance(document, dict)
        and document.get("contract_version") == version
        and required <= set(document)
        and document.get("canonical_hash") == contract_payload_hash(document)
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _source_hash(extraction: dict) -> str:
    return extraction.get("source_artifact_hash") or extraction.get("raw_content_hash") or extraction["input_ref"]["canonical_hash"]


def build_confirmation_queue(case_id: str, bundles: list[dict]) -> dict:
    requests = []
    for bundle in bundles:
        extraction = bundle.get("extraction", {})
        if extraction.get("verification_status") != "unverified_extraction":
            continue
        source_hash = _source_hash(extraction)
        request = {
            "contract_version": "nhi.confirmation_request.v1",
            "request_id": f"confirmation_request_{canonical_sha256([case_id, extraction['extraction_id'], source_hash])[:16]}",
            "source_extraction_id": extraction["extraction_id"], "source_type": extraction["source_type"],
            "source_artifact_hash": source_hash, "extracted_fields": copy.deepcopy(extraction.get("extracted_fields", {})),
            "field_confidences": copy.deepcopy(extraction.get("field_confidence", {})),
            "reason_confirmation_required": "Source extraction requires human confirmation before use.",
            "allowed_actions": list(ACTIONS), "created_timestamp": _timestamp(),
        }
        request["canonical_hash"] = contract_payload_hash(request)
        requests.append(request)
    queue = {
        "contract_version": "nhi.confirmation_queue.v1",
        "queue_id": f"confirmation_queue_{canonical_sha256([case_id, [r['request_id'] for r in requests]])[:16]}",
        "case_id": case_id, "requests": requests, "pending_count": len(requests),
        "created_timestamp": _timestamp(),
    }
    queue["canonical_hash"] = contract_payload_hash(queue)
    return queue


def _match(response: dict, requests: list[dict]) -> tuple[dict, str]:
    candidates = [item for item in requests if item["request_id"] == response.get("request_id")]
    method = "request_id"
    if not candidates and response.get("source_extraction_id"):
        candidates = [item for item in requests if item["source_extraction_id"] == response["source_extraction_id"]]
        method = "source_extraction_id"
    if not candidates and response.get("source_artifact_hash"):
        candidates = [item for item in requests if item["source_artifact_hash"] == response["source_artifact_hash"]]
        method = "source_artifact_hash"
    if len(candidates) > 1:
        raise ValueError("CONFIRMATION_PAIR_AMBIGUOUS")
    if not candidates:
        raise ValueError("CONFIRMATION_PAIR_NOT_FOUND")
    request = candidates[0]
    supplied_hash = response.get("source_artifact_hash")
    if supplied_hash and supplied_hash != request["source_artifact_hash"]:
        raise ValueError("CONFIRMATION_SOURCE_STALE")
    return request, method


def apply_confirmation_responses(queue: dict, responses: list[dict], bundles: list[dict]) -> dict:
    if not _valid(queue, "nhi.confirmation_queue.v1", {"queue_id", "case_id", "requests", "pending_count", "created_timestamp", "canonical_hash"}):
        raise ValueError("CONFIRMATION_QUEUE_INVALID")
    working = {bundle["extraction"]["extraction_id"]: copy.deepcopy(bundle) for bundle in bundles}
    unresolved = {request["request_id"] for request in queue["requests"]}
    pairs = []
    discarded = []
    for response in responses:
        if not _valid(response, "nhi.confirmation_response.v1", {"response_id", "request_id", "action", "confirmed_fields", "corrected_fields", "created_timestamp", "canonical_hash"}) or response.get("action") not in ACTIONS:
            raise ValueError("CONFIRMATION_RESPONSE_INVALID")
        request, method = _match(response, queue["requests"])
        extraction_id = request["source_extraction_id"]
        bundle = working.get(extraction_id)
        if bundle is None or _source_hash(bundle["extraction"]) != request["source_artifact_hash"]:
            raise ValueError("CONFIRMATION_SOURCE_STALE")
        action = response["action"]
        if action in {"confirm", "correct"}:
            legacy = {
                "contract_version": "nhi.host_user_confirmation.v1",
                "confirmation_id": response["response_id"],
                "extraction_ref": {"extraction_id": extraction_id, "canonical_hash": bundle["extraction"]["canonical_hash"]},
                "action": action, "corrections": response.get("corrected_fields", {}), "confirmed_by_human": True,
            }
            legacy["canonical_hash"] = contract_payload_hash(legacy)
            working[extraction_id] = apply_confirmation(bundle, legacy)
            unresolved.discard(request["request_id"])
        elif action == "discard":
            working.pop(extraction_id, None); discarded.append(extraction_id); unresolved.discard(request["request_id"])
        pairs.append({"request_id": request["request_id"], "response_id": response["response_id"], "source_extraction_id": extraction_id, "source_artifact_hash": request["source_artifact_hash"], "action": action, "match_method": method})
    pairing = {
        "contract_version": "nhi.confirmation_pairing.v1",
        "pairing_id": f"confirmation_pairing_{canonical_sha256([queue['queue_id'], pairs])[:16]}",
        "queue_ref": {"queue_id": queue["queue_id"], "canonical_hash": queue["canonical_hash"]},
        "pairs": pairs, "unresolved_request_ids": sorted(unresolved), "discarded_extraction_ids": discarded,
        "created_timestamp": _timestamp(),
    }
    pairing["canonical_hash"] = contract_payload_hash(pairing)
    return {"bundles": list(working.values()), "pairing": pairing, "unresolved_count": len(unresolved)}


def pair_confirmation_responses(queue: dict, responses: list[dict]) -> dict:
    """Pair response artifacts without requiring the original evidence documents."""
    if not _valid(queue, "nhi.confirmation_queue.v1", {"queue_id", "case_id", "requests", "pending_count", "created_timestamp", "canonical_hash"}):
        raise ValueError("CONFIRMATION_QUEUE_INVALID")
    unresolved = {request["request_id"] for request in queue["requests"]}
    pairs = []
    discarded = []
    for response in responses:
        if not _valid(response, "nhi.confirmation_response.v1", {"response_id", "request_id", "action", "confirmed_fields", "corrected_fields", "created_timestamp", "canonical_hash"}) or response.get("action") not in ACTIONS:
            raise ValueError("CONFIRMATION_RESPONSE_INVALID")
        request, method = _match(response, queue["requests"])
        pairs.append({"request_id": request["request_id"], "response_id": response["response_id"], "source_extraction_id": request["source_extraction_id"], "source_artifact_hash": request["source_artifact_hash"], "action": response["action"], "match_method": method})
        if response["action"] != "defer":
            unresolved.discard(request["request_id"])
        if response["action"] == "discard":
            discarded.append(request["source_extraction_id"])
    result = {
        "contract_version": "nhi.confirmation_pairing.v1",
        "pairing_id": f"confirmation_pairing_{canonical_sha256([queue['queue_id'], pairs])[:16]}",
        "queue_ref": {"queue_id": queue["queue_id"], "canonical_hash": queue["canonical_hash"]},
        "pairs": pairs, "unresolved_request_ids": sorted(unresolved),
        "discarded_extraction_ids": discarded, "created_timestamp": _timestamp(),
    }
    result["canonical_hash"] = contract_payload_hash(result)
    return result
