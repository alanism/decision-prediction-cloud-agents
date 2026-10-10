"""Local file import capability constrained by the caller's local root."""

from __future__ import annotations

import hashlib
from pathlib import Path

from capital_decision_lab.privacy.containment import validate_contained_path


def file_import_capability(local_root: Path):
    def retrieve(request) -> dict:
        check = validate_contained_path(local_root, Path(str(request.artifact_path or "")))
        if not check["allowed"]:
            raise ValueError(check["issues"][0]["code"])
        path = Path(check["resolved_path"])
        raw = path.read_text(encoding="utf-8")
        return {"raw_content": raw, "source_artifact_hash": hashlib.sha256(path.read_bytes()).hexdigest(), "confidence": 1.0}
    return retrieve
