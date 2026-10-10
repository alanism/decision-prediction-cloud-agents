"""Host-neutral capability ingestion and extraction eligibility boundary."""

from __future__ import annotations

import copy

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.host.extractors import EXTRACTORS
from capital_decision_lab.host.miniloops import prompt_for


CAPABILITIES = (
    "browser_current_page", "browser_fetch_url", "browser_extract_selection",
    "screenshot_capture", "screenshot_ocr", "authenticated_session_fetch",
    "local_file_picker", "clipboard_read", "user_confirmation",
)
USABLE_STATUSES = {"auto_retrieved", "user_verified", "user_corrected"}


def ingest_capability_response(document: dict) -> dict:
    if validate_contract(document) or document.get("canonical_hash") != contract_payload_hash(document):
        raise ValueError("HOST_CAPABILITY_RESPONSE_INVALID")
    return copy.deepcopy(document)


def analysis_eligibility(document: dict) -> dict:
    if document.get("contract_version") != "nhi.host_extraction_result.v1":
        return {"eligible": False, "issues": [{"code": "SOURCE_SPECIFIC_EXTRACTION_REQUIRED"}]}
    if validate_contract(document) or document.get("canonical_hash") != contract_payload_hash(document):
        return {"eligible": False, "issues": [{"code": "HOST_EXTRACTION_INVALID"}]}
    if document.get("verification_status") not in USABLE_STATUSES:
        return {"eligible": False, "issues": [{"code": "HOST_EXTRACTION_CONFIRMATION_REQUIRED"}]}
    return {"eligible": True, "issues": []}


def extract_source(source_type: str, response: dict) -> dict:
    extractor = EXTRACTORS.get(source_type)
    if extractor is None:
        return {"status": "blocked_source_unavailable", "issues": [{"code": "HOST_EXTRACTOR_UNKNOWN"}], "mini_loop": prompt_for(source_type)}
    try:
        bundle = extractor(response)
    except (KeyError, TypeError, ValueError) as exc:
        return {"status": "blocked_missing_user_input", "issues": [{"code": str(exc)}], "mini_loop": prompt_for(source_type, reason=str(exc))}
    return {"status": "ok", "issues": [], "extraction_bundle": bundle}
