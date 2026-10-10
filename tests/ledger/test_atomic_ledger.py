from __future__ import annotations

import copy
import json
from pathlib import Path

from capital_decision_lab.contracts import ledger
from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.orchestration.analyze import analyze_case


ROOT = Path(__file__).resolve().parents[2]


def _documents(authorization_id: str = "authorization_ledger_001") -> tuple[dict, dict, dict]:
    case = json.loads((ROOT / "fixtures" / "valid" / "mvp-case.json").read_text(encoding="utf-8"))
    analysis = analyze_case(case, alternative_id="alt_a")
    proposal = {
        "contract_version": "nhi.decision_proposal.v1",
        "proposal_id": "proposal_ledger_001",
        "analysis_ref": {"analysis_id": analysis["analysis_id"], "canonical_hash": analysis["canonical_hash"]},
        "selected_action": {
            "value": {"alternative_id": "alt_a", "exposure": 0.05},
            "provenance_class": "decided",
            "input_refs": [analysis["analysis_id"]],
        },
    }
    proposal["canonical_hash"] = contract_payload_hash(proposal)
    authorization = {
        "contract_version": "nhi.decision_authorization.v1",
        "authorization_id": authorization_id,
        "proposal_ref": {
            "proposal_id": proposal["proposal_id"],
            "canonical_hash": proposal["canonical_hash"],
            "document_path": "../proposals/proposal_ledger_001.json",
        },
        "analysis_ref": {"analysis_id": analysis["analysis_id"], "canonical_hash": analysis["canonical_hash"]},
        "confirmed_by_human": True,
    }
    authorization["canonical_hash"] = contract_payload_hash(authorization)
    return proposal, analysis, authorization


def test_atomic_append_requires_valid_binding(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    path = local_root / "ledger" / "decision-ledger.json"
    proposal, analysis, authorization = _documents()
    result = ledger.append_authorized_entry(
        path, proposal, analysis, authorization, local_root=local_root
    )
    assert result["success"] is True
    assert result["appended"] is True
    document = json.loads(path.read_text(encoding="utf-8"))
    assert validate_contract(document) == []
    assert len(document["entries"]) == 1


def test_identical_replay_is_idempotent(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    path = local_root / "ledger.json"
    proposal, analysis, authorization = _documents()
    first = ledger.append_authorized_entry(path, proposal, analysis, authorization, local_root=local_root)
    before = path.read_bytes()
    second = ledger.append_authorized_entry(path, proposal, analysis, authorization, local_root=local_root)
    assert first["appended"] is True
    assert second["success"] is True and second["appended"] is False
    assert path.read_bytes() == before


def test_conflicting_replay_is_rejected(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    path = local_root / "ledger.json"
    proposal, analysis, authorization = _documents()
    assert ledger.append_authorized_entry(path, proposal, analysis, authorization, local_root=local_root)["success"]
    conflict = copy.deepcopy(authorization)
    conflict["proposal_ref"]["document_path"] = "../proposals/alternate.json"
    conflict["canonical_hash"] = contract_payload_hash(conflict)
    result = ledger.append_authorized_entry(path, proposal, analysis, conflict, local_root=local_root)
    assert result["success"] is False
    assert result["issues"] == [{"code": "LEDGER_REPLAY_CONFLICT"}]


def test_binding_failure_produces_no_ledger(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    path = local_root / "ledger.json"
    proposal, analysis, authorization = _documents()
    authorization["analysis_ref"]["canonical_hash"] = "f" * 64
    authorization["canonical_hash"] = contract_payload_hash(authorization)
    result = ledger.append_authorized_entry(path, proposal, analysis, authorization, local_root=local_root)
    assert result["success"] is False
    assert not path.exists()


def test_replace_failure_preserves_existing_ledger(tmp_path: Path, monkeypatch) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    path = local_root / "ledger.json"
    proposal, analysis, authorization = _documents()
    assert ledger.append_authorized_entry(path, proposal, analysis, authorization, local_root=local_root)["success"]
    before = path.read_bytes()
    _, _, second_authorization = _documents("authorization_ledger_002")

    def fail_replace(source, destination):
        raise OSError("injected replace failure")

    monkeypatch.setattr(ledger.os, "replace", fail_replace)
    result = ledger.append_authorized_entry(
        path, proposal, analysis, second_authorization, local_root=local_root
    )
    assert result["success"] is False
    assert result["issues"] == [{"code": "LEDGER_ATOMIC_WRITE_FAILED"}]
    assert path.read_bytes() == before


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    proposal, analysis, authorization = _documents()
    result = ledger.append_authorized_entry(
        tmp_path / "outside.json",
        proposal,
        analysis,
        authorization,
        local_root=local_root,
    )
    assert result["success"] is False
    assert result["issues"] == [{"code": "PATH_ESCAPE_FORBIDDEN"}]
