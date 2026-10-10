"""Verification gates for locally supplied evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.privacy.containment import validate_contained_path


ELIGIBLE_STATUSES = {"auto_retrieved", "user_verified", "user_corrected"}


def update_eligibility(document: dict) -> dict:
    status = document.get("verification_status") if isinstance(document, dict) else None
    if status in ELIGIBLE_STATUSES:
        return {"eligible": True, "issues": []}
    return {"eligible": False, "issues": [{"code": "EVIDENCE_NOT_VERIFIED"}]}


def validate_local_evidence(document: dict, local_root: Path) -> list[dict]:
    """Validate a contract plus any contained artifact path and SHA-256 reference."""
    issues = list(validate_contract(document))
    references = list(document.get("artifact_refs", [])) if isinstance(document, dict) else []
    screenshot = document.get("screenshot_artifact") if isinstance(document, dict) else None
    if isinstance(screenshot, dict):
        references.append(screenshot)
    for index, reference in enumerate(references):
        if not isinstance(reference, dict):
            issues.append({"code": "EVIDENCE_ARTIFACT_REFERENCE_INVALID", "path": f"$.artifact_refs[{index}]"})
            continue
        check = validate_contained_path(local_root, Path(str(reference.get("path", ""))))
        if not check["allowed"]:
            issues.extend({**item, "path": f"$.artifact_refs[{index}].path"} for item in check["issues"])
            continue
        path = Path(check["resolved_path"])
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            issues.append({"code": "EVIDENCE_ARTIFACT_UNREADABLE", "path": f"$.artifact_refs[{index}].path"})
            continue
        if actual != reference.get("sha256"):
            issues.append({"code": "EVIDENCE_ARTIFACT_HASH_MISMATCH", "path": f"$.artifact_refs[{index}].sha256"})
    return issues
