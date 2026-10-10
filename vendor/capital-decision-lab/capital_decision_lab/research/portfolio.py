"""Portfolio contract and source-artifact validation."""

from __future__ import annotations

import hashlib
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.privacy.containment import validate_contained_path
from capital_decision_lab.contracts.canonical import canonical_sha256


def import_portfolio_file(path: Path) -> dict:
    """Import structured JSON/CSV; images remain blocked pending host extraction."""
    candidate = Path(path)
    if candidate.suffix.casefold() == ".json":
        try:
            document = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"status": "blocked_low_confidence", "issues": [{"code": "PORTFOLIO_FILE_INVALID"}]}
        return {"status": "ok", "portfolio": document, "issues": []}
    if candidate.suffix.casefold() != ".csv":
        return {"status": "blocked_low_confidence", "issues": [{"code": "PORTFOLIO_EXTRACTION_CAPABILITY_REQUIRED"}]}
    try:
        with candidate.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError:
        return {"status": "blocked_source_unavailable", "issues": [{"code": "PORTFOLIO_FILE_UNREADABLE"}]}
    required = {"ticker", "shares", "current_price", "user_intent", "cash", "borrowed_amount", "maintenance_margin_requirement", "initial_margin_requirement"}
    if not rows or not required <= set(rows[0]):
        return {"status": "blocked_missing_user_input", "issues": [{"code": "PORTFOLIO_CSV_FIELDS_REQUIRED", "missing": sorted(required - set(rows[0] if rows else []))}]}
    try:
        cash = float(rows[0]["cash"]); borrowed = float(rows[0]["borrowed_amount"])
        positions = []
        gross = 0.0
        for row in rows:
            shares = float(row["shares"]); price = float(row["current_price"]); market_value = shares * price; gross += market_value
            positions.append({"ticker": row["ticker"], "shares": shares, "current_price": price, "market_value": market_value, "position_weight": 0.0, "user_intent": row["user_intent"]})
        equity = gross + cash - borrowed
        for position in positions:
            position["position_weight"] = position["market_value"] / equity if equity else 0.0
        document = {
            "contract_version": "nhi.portfolio_snapshot.v1", "snapshot_id": f"portfolio_{canonical_sha256(rows)[:16]}",
            "capture_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "cash": cash, "total_equity": equity, "margin_used": borrowed, "borrowed_amount": borrowed,
            "maintenance_margin_requirement": float(rows[0]["maintenance_margin_requirement"]),
            "initial_margin_requirement": float(rows[0]["initial_margin_requirement"]),
            "portfolio_source": "csv", "positions": positions, "verification_status": "unverified_extraction",
        }
    except (KeyError, TypeError, ValueError):
        return {"status": "blocked_low_confidence", "issues": [{"code": "PORTFOLIO_CSV_VALUE_INVALID"}]}
    return {"status": "ok", "portfolio": document, "issues": []}


def validate_portfolio_snapshot(document: dict, local_root: Path) -> list[dict]:
    issues = list(validate_contract(document))
    artifact_path = document.get("source_artifact_path")
    artifact_hash = document.get("source_artifact_hash")
    if artifact_path is None and artifact_hash is None:
        return issues
    if not isinstance(artifact_path, str) or not isinstance(artifact_hash, str):
        return issues + [{"code": "PORTFOLIO_ARTIFACT_REFERENCE_INCOMPLETE", "path": "$.source_artifact_path"}]
    check = validate_contained_path(local_root, Path(artifact_path))
    if not check["allowed"]:
        return issues + check["issues"]
    try:
        actual = hashlib.sha256(Path(check["resolved_path"]).read_bytes()).hexdigest()
    except OSError:
        return issues + [{"code": "PORTFOLIO_ARTIFACT_UNREADABLE", "path": "$.source_artifact_path"}]
    if actual != artifact_hash:
        issues.append({"code": "PORTFOLIO_ARTIFACT_HASH_MISMATCH", "path": "$.source_artifact_hash"})
    return issues
