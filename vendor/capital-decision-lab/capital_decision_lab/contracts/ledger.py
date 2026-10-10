"""Atomic, idempotent local ledger append after authorization validation."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path

from capital_decision_lab.contracts.authorization import validate_binding
from capital_decision_lab.contracts.canonical import canonical_json, canonical_sha256
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.privacy.containment import validate_contained_path


def _failure(code: str) -> dict:
    return {"success": False, "appended": False, "issues": [{"code": code}]}


def _ledger_hash(document: dict) -> str:
    payload = copy.deepcopy(document)
    payload.pop("ledger_hash", None)
    return canonical_sha256(payload)


def _new_ledger() -> dict:
    document = {
        "contract_version": "nhi.decision_ledger.v1",
        "ledger_id": "nhi-capital-local",
        "entries": [],
    }
    document["ledger_hash"] = _ledger_hash(document)
    return document


def _load_ledger(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return _new_ledger(), None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "LEDGER_READ_FAILED"
    if validate_contract(document) or document.get("ledger_hash") != _ledger_hash(document):
        return None, "LEDGER_INTEGRITY_INVALID"
    return document, None


def _write_atomic(path: Path, document: dict) -> str | None:
    temporary: Path | None = None
    try:
        directory = path.parents[0]
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=directory,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(canonical_json(document))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        return None
    except OSError:
        return "LEDGER_ATOMIC_WRITE_FAILED"
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def append_authorized_entry(
    path: Path,
    proposal: dict,
    analysis: dict,
    authorization: dict,
    *,
    local_root: Path,
) -> dict:
    """Append one hash-bound record or return an idempotent replay result."""
    containment = validate_contained_path(Path(local_root), Path(path))
    if not containment["allowed"]:
        return _failure(containment["issues"][0]["code"])
    ledger_path = Path(containment["resolved_path"])

    binding_issues = validate_binding(proposal, analysis, authorization)
    if binding_issues:
        return {"success": False, "appended": False, "issues": binding_issues}
    document, load_error = _load_ledger(ledger_path)
    if load_error:
        return _failure(load_error)

    proposal_hash = proposal["canonical_hash"]
    analysis_hash = analysis["canonical_hash"]
    authorization_hash = authorization["canonical_hash"]
    authorization_id = authorization["authorization_id"]
    prior = next(
        (item for item in document["entries"] if item["authorization_id"] == authorization_id),
        None,
    )
    if prior is not None:
        same = (
            prior["proposal_hash"] == proposal_hash
            and prior["analysis_hash"] == analysis_hash
            and prior["authorization_hash"] == authorization_hash
        )
        if not same:
            return _failure("LEDGER_REPLAY_CONFLICT")
        return {
            "success": True,
            "appended": False,
            "issues": [],
            "ledger_hash": document["ledger_hash"],
            "entry_hash": prior["entry_hash"],
        }

    previous_hash = document["entries"][-1]["entry_hash"] if document["entries"] else None
    entry = {
        "entry_id": f"entry_{canonical_sha256({'authorization_id': authorization_id})[:16]}",
        "authorization_id": authorization_id,
        "proposal_hash": proposal_hash,
        "analysis_hash": analysis_hash,
        "authorization_hash": authorization_hash,
        "previous_entry_hash": previous_hash,
    }
    entry["entry_hash"] = canonical_sha256(entry)
    updated = copy.deepcopy(document)
    updated["entries"].append(entry)
    updated["ledger_hash"] = _ledger_hash(updated)
    if validate_contract(updated):
        return _failure("LEDGER_CONTRACT_INVALID")
    write_error = _write_atomic(ledger_path, updated)
    if write_error:
        return _failure(write_error)
    return {
        "success": True,
        "appended": True,
        "issues": [],
        "ledger_hash": updated["ledger_hash"],
        "entry_hash": entry["entry_hash"],
    }
