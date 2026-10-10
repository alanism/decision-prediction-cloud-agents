"""Atomic, authorization-gated local recommendation records."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from capital_decision_lab.contracts.canonical import canonical_json, canonical_sha256, contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.privacy.containment import validate_contained_path


def _failure(code: str) -> dict:
    return {"success": False, "appended": False, "issues": [{"code": code}]}


def _ledger_hash(document: dict) -> str:
    payload = copy.deepcopy(document); payload.pop("ledger_hash", None)
    return canonical_sha256(payload)


def _write_atomic(path: Path, document: dict) -> None:
    temporary = None
    try:
        directory = path.parents[0]
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(canonical_json(document) + "\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def record_recommendation(path: Path, recommendation: dict, authorization: dict, *, local_root: Path) -> dict:
    check = validate_contained_path(local_root, path)
    if not check["allowed"]:
        return _failure(check["issues"][0]["code"])
    if validate_contract(recommendation) or recommendation.get("canonical_hash") != contract_payload_hash(recommendation):
        return _failure("RECOMMENDATION_INVALID")
    if validate_contract(authorization) or authorization.get("canonical_hash") != contract_payload_hash(authorization):
        return _failure("RECOMMENDATION_AUTHORIZATION_INVALID")
    reference = authorization["recommendation_ref"]
    if reference["recommendation_id"] != recommendation["recommendation_id"] or reference["canonical_hash"] != recommendation["canonical_hash"]:
        return _failure("RECOMMENDATION_AUTHORIZATION_MISMATCH")
    ledger_path = Path(check["resolved_path"])
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"entries": []}
    except (OSError, json.JSONDecodeError):
        return _failure("RECOMMENDATION_LEDGER_INVALID")
    if ledger_path.exists() and ledger.get("ledger_hash") != _ledger_hash(ledger):
        return _failure("RECOMMENDATION_LEDGER_INTEGRITY_INVALID")
    prior = next((entry for entry in ledger["entries"] if entry["authorization_id"] == authorization["authorization_id"]), None)
    if prior is not None:
        same = prior["recommendation_hash"] == recommendation["canonical_hash"] and prior["user_authorization_hash"] == authorization["canonical_hash"]
        return {"success": same, "appended": False, "issues": [] if same else [{"code": "RECOMMENDATION_REPLAY_CONFLICT"}]}
    entry = {
        "authorization_id": authorization["authorization_id"],
        "portfolio_snapshot_hash": recommendation["portfolio_snapshot_hash"],
        "evidence_hash": recommendation["evidence_synthesis_hash"],
        "belief_update_hash": authorization["belief_update_hash"],
        "recommendation_hash": recommendation["canonical_hash"],
        "user_authorization_hash": authorization["canonical_hash"],
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "previous_entry_hash": ledger["entries"][-1]["entry_hash"] if ledger["entries"] else None,
    }
    entry["entry_hash"] = canonical_sha256(entry)
    updated = copy.deepcopy(ledger); updated["entries"].append(entry); updated["ledger_hash"] = _ledger_hash(updated)
    try:
        _write_atomic(ledger_path, updated)
    except OSError:
        return _failure("RECOMMENDATION_LEDGER_WRITE_FAILED")
    return {"success": True, "appended": True, "issues": []}
