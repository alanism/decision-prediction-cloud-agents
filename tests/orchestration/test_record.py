from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.orchestration import analyze, record


ROOT = Path(__file__).resolve().parents[2]


def _write_documents(local_root: Path) -> tuple[Path, Path]:
    case = json.loads((ROOT / "fixtures" / "valid" / "mvp-case.json").read_text(encoding="utf-8"))
    analysis = analyze.analyze_case(case, alternative_id="alt_a")
    proposal = {
        "contract_version": "nhi.decision_proposal.v1",
        "proposal_id": "proposal_record_001",
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
        "authorization_id": "authorization_record_001",
        "proposal_ref": {
            "proposal_id": proposal["proposal_id"],
            "canonical_hash": proposal["canonical_hash"],
            "document_path": "../proposals/proposal.json",
        },
        "analysis_ref": {"analysis_id": analysis["analysis_id"], "canonical_hash": analysis["canonical_hash"]},
        "confirmed_by_human": True,
    }
    authorization["canonical_hash"] = contract_payload_hash(authorization)
    paths = {
        "analysis": local_root / "analyses" / "analysis.json",
        "proposal": local_root / "proposals" / "proposal.json",
        "authorization": local_root / "authorizations" / "authorization.json",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["analysis"].write_text(json.dumps(analysis), encoding="utf-8")
    paths["proposal"].write_text(json.dumps(proposal), encoding="utf-8")
    paths["authorization"].write_text(json.dumps(authorization), encoding="utf-8")
    return paths["analysis"], paths["authorization"]


def test_record_resolves_separate_proposal_and_appends(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    analysis_path, authorization_path = _write_documents(local_root)
    result = record.record_from_files(
        analysis_path, authorization_path, local_root=local_root
    )
    assert result["success"] is True
    assert result["appended"] is True
    assert (local_root / "ledger" / "decision-ledger.json").is_file()


def test_record_rejects_proposal_path_escape(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    analysis_path, authorization_path = _write_documents(local_root)
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    authorization["proposal_ref"]["document_path"] = "../../outside.json"
    authorization["canonical_hash"] = contract_payload_hash(authorization)
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    result = record.record_from_files(
        analysis_path, authorization_path, local_root=local_root
    )
    assert result["success"] is False
    assert result["issues"] == [{"code": "PATH_ESCAPE_FORBIDDEN"}]
    assert not (local_root / "ledger").exists()

