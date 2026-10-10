"""Contained local artifact and hash validation for host-provided sources."""

from __future__ import annotations

import hashlib
from pathlib import Path

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.privacy.containment import validate_contained_path


def validate_host_artifact(document: dict, local_root: Path) -> list[dict]:
    issues = list(validate_contract(document))
    if document.get("canonical_hash") != contract_payload_hash(document):
        issues.append({"code": "HOST_ARTIFACT_CANONICAL_HASH_INVALID", "path": "$.canonical_hash"})
    check = validate_contained_path(local_root, Path(str(document.get("artifact_path", ""))))
    if not check["allowed"]:
        return issues + check["issues"]
    try:
        actual = hashlib.sha256(Path(check["resolved_path"]).read_bytes()).hexdigest()
    except OSError:
        return issues + [{"code": "HOST_ARTIFACT_UNREADABLE", "path": "$.artifact_path"}]
    if actual != document.get("artifact_hash"):
        issues.append({"code": "HOST_ARTIFACT_HASH_MISMATCH", "path": "$.artifact_hash"})
    return issues
