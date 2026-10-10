"""Contained file resolution for authorized local ledger recording."""

from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.contracts.ledger import append_authorized_entry
from capital_decision_lab.privacy.containment import validate_contained_path


def _failure(code: str) -> dict:
    return {"success": False, "appended": False, "issues": [{"code": code}]}


def _load(root: Path, path: Path) -> tuple[dict | None, dict | None]:
    containment = validate_contained_path(root, path)
    if not containment["allowed"]:
        return None, _failure(containment["issues"][0]["code"])
    try:
        value = json.loads(Path(containment["resolved_path"]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, _failure("LOCAL_DOCUMENT_INVALID")
    if not isinstance(value, dict):
        return None, _failure("LOCAL_DOCUMENT_INVALID")
    return value, None


def record_from_files(
    analysis_path: Path,
    authorization_path: Path,
    *,
    local_root: Path,
) -> dict:
    root = Path(local_root).resolve(strict=True)
    analysis, failure = _load(root, Path(analysis_path))
    if failure:
        return failure
    authorization, failure = _load(root, Path(authorization_path))
    if failure:
        return failure
    proposal_relative = authorization.get("proposal_ref", {}).get("document_path")
    if not isinstance(proposal_relative, str):
        return _failure("PROPOSAL_PATH_REQUIRED")
    proposal_path = Path(authorization_path).resolve().parents[0] / proposal_relative
    proposal, failure = _load(root, proposal_path)
    if failure:
        return failure
    return append_authorized_entry(
        root / "ledger" / "decision-ledger.json",
        proposal,
        analysis,
        authorization,
        local_root=root,
    )
