from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.recommendation.records import record_recommendation
from tests.recommendation.test_recommendation_engine import inputs
from capital_decision_lab.recommendation.engine import build_recommendation


def authorization(recommendation: dict, **overrides) -> dict:
    document = {
        "contract_version": "nhi.recommendation_authorization.v1",
        "authorization_id": "recommendation_auth_1",
        "recommendation_ref": {"recommendation_id": recommendation["recommendation_id"], "canonical_hash": recommendation["canonical_hash"]},
        "authorization_action": "accept_recommendation", "confirmed_by_human": True,
        "belief_update_hash": "9" * 64,
    }
    document.update(overrides)
    document["canonical_hash"] = contract_payload_hash(document)
    return document


def test_recommendation_requires_hash_bound_human_authorization(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    recommendation = build_recommendation(inputs())
    denied = authorization(recommendation, confirmed_by_human=False)
    assert record_recommendation(local / "ledger.json", recommendation, denied, local_root=local)["success"] is False
    mismatch = authorization(recommendation)
    mismatch["recommendation_ref"]["canonical_hash"] = "0" * 64
    mismatch["canonical_hash"] = contract_payload_hash(mismatch)
    assert record_recommendation(local / "ledger.json", recommendation, mismatch, local_root=local)["success"] is False


def test_authorized_record_stores_required_hashes_atomically(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    recommendation = build_recommendation(inputs())
    auth = authorization(recommendation)
    result = record_recommendation(local / "ledger.json", recommendation, auth, local_root=local)
    assert result["success"] is True and result["appended"] is True
    ledger = json.loads((local / "ledger.json").read_text(encoding="utf-8"))
    entry = ledger["entries"][0]
    assert entry["portfolio_snapshot_hash"] == recommendation["portfolio_snapshot_hash"]
    assert entry["evidence_hash"] == recommendation["evidence_synthesis_hash"]
    assert entry["belief_update_hash"] == auth["belief_update_hash"]
    assert entry["recommendation_hash"] == recommendation["canonical_hash"]
    assert entry["user_authorization_hash"] == auth["canonical_hash"]


def test_identical_replay_is_idempotent(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    recommendation = build_recommendation(inputs())
    auth = authorization(recommendation)
    first = record_recommendation(local / "ledger.json", recommendation, auth, local_root=local)
    second = record_recommendation(local / "ledger.json", recommendation, auth, local_root=local)
    assert first["appended"] is True
    assert second["success"] is True and second["appended"] is False


def test_tampered_recommendation_ledger_is_rejected(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    recommendation = build_recommendation(inputs()); auth = authorization(recommendation)
    path = local / "ledger.json"
    assert record_recommendation(path, recommendation, auth, local_root=local)["success"] is True
    ledger = json.loads(path.read_text(encoding="utf-8")); ledger["entries"][0]["evidence_hash"] = "0" * 64
    path.write_text(json.dumps(ledger), encoding="utf-8")
    result = record_recommendation(path, recommendation, auth, local_root=local)
    assert result["issues"] == [{"code": "RECOMMENDATION_LEDGER_INTEGRITY_INVALID"}]
