from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.plugin.commands import run_cli


def _write(root: Path, name: str, value: dict) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _snapshot() -> dict:
    return {
        "contract_version": "nhi.event_market_snapshot.v1", "snapshot_id": "market_1",
        "source_type": "polymarket", "verification_status": "user_verified", "title": "Synthetic",
        "event_domain": "geopolitics", "event_category": "shipping_disruption",
        "captured_at": "2026-07-01T00:00:00Z", "outcomes": [
            {"name": "Disruption", "probability": 0.7, "tags": ["disruption", "oil_shock"]},
            {"name": "Normal", "probability": 0.3, "tags": ["normalization"]},
        ], "total_volume": 100000, "resolution_rules": "Synthetic rule",
    }


def test_evidence_validate_analyze_alias_and_social(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    snapshot = _write(local, "snapshot.json", _snapshot())
    batch = _write(local, "batch.json", {
        "contract_version": "nhi.evidence_batch.v1", "batch_id": "batch_1", "source_type": "reddit",
        "verification_status": "user_verified", "items": [{"item_id": "one", "source_type": "reddit", "verification_status": "user_verified", "direction": "bullish", "timestamp": "2026-06-30T00:00:00Z", "captured_at": "2026-07-01T00:00:00Z", "subreddit": "synthetic", "score": 3, "claim_tags": ["claim"], "source_credibility": 0.8, "thesis_relevance": 0.8}],
    })
    for args in (
        ["evidence", "validate", "--file", str(snapshot)],
        ["evidence", "analyze-event-market", "--snapshot", str(snapshot)],
        ["evidence", "analyze-polymarket", "--snapshot", str(snapshot)],
        ["evidence", "analyze-social", "--batch", str(batch)],
    ):
        code, result = run_cli(args, local_root=local)
        assert code == 0, result
        assert result["network_attempts"] == result["model_calls"] == 0


def test_synthesis_belief_and_proposal_commands(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    snapshot = _write(local, "snapshot.json", _snapshot())
    _, analyzed = run_cli(["evidence", "analyze-event-market", "--snapshot", str(snapshot)], local_root=local)
    signal = analyzed["signal"]
    inputs = _write(local, "signals.json", {"signals": [signal]})
    _, synthesized = run_cli(["evidence", "synthesize", "--inputs", str(inputs)], local_root=local)
    synthesis = _write(local, "synthesis.json", synthesized["synthesis"])
    root = Path(__file__).resolve().parents[2]
    case = _write(local, "case.json", json.loads((root / "fixtures" / "valid" / "mvp-case.json").read_text(encoding="utf-8")))
    sensitivity_value = {"contract_version": "nhi.thesis_sensitivity_map.v1", "map_id": "map_1", "target_asset": {"ticker": "SYNTH"}, "sensitivity_rules": [{"source_type": "polymarket", "event_domain": "geopolitics", "event_category": "shipping_disruption", "impact_channel": "oil_shock", "direction_for_thesis": "bearish", "sensitivity": "high", "affected_assumption": "win_probability"}]}
    sensitivity_value["canonical_hash"] = contract_payload_hash(sensitivity_value)
    sensitivity = _write(local, "sensitivity.json", sensitivity_value)
    code, result = run_cli(["belief", "update", "--case", str(case), "--synthesis", str(synthesis), "--sensitivity", str(sensitivity)], local_root=local)
    assert code == 0
    update = _write(local, "update.json", result["belief_update"])
    code, result = run_cli(["assumption", "propose", "--belief-update", str(update)], local_root=local)
    assert code == 0
    assert result["proposal"]["approval_status"] == "pending"


def test_no_live_fetch_commands_exist() -> None:
    for argv in (["evidence", "fetch"], ["evidence", "polymarket-api"], ["evidence", "reddit-api"]):
        try:
            run_cli(argv)
        except SystemExit as exc:
            assert exc.code != 0
        else:
            raise AssertionError(f"unexpected live command: {argv}")


def test_only_approved_proposal_changes_main_analysis(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    root = Path(__file__).resolve().parents[2]
    case = _write(local, "case.json", json.loads((root / "fixtures" / "valid" / "mvp-case.json").read_text(encoding="utf-8")))
    proposal = {
        "contract_version": "nhi.assumption_update_proposal.v1", "proposal_id": "proposal_1",
        "prior_assumption": {"name": "win_probability", "value": 0.6},
        "proposed_assumption": {"name": "win_probability", "value": 0.55, "provenance_class": "forecast"},
        "evidence_refs": ["evidence_1"], "evidence_batch_hash": "a" * 64,
        "synthesis_hash": "b" * 64, "sensitivity_map_hash": "c" * 64,
        "bayesian_update_hash": "d" * 64, "affected_metric": "win_probability",
        "affected_thesis_scenario": "base", "projected_impacts": {},
        "approval_status": "pending", "canonical_hash": "e" * 64,
    }
    pending = _write(local, "pending.json", proposal)
    approved = _write(local, "approved.json", {**proposal, "approval_status": "approved"})
    _, baseline = run_cli(["analyze", "--case", str(case)], local_root=local)
    _, unchanged = run_cli(["analyze", "--case", str(case), "--assumption-update", str(pending)], local_root=local)
    _, changed = run_cli(["analyze", "--case", str(case), "--assumption-update", str(approved)], local_root=local)
    assert unchanged["analysis"]["data"]["kelly"]["value"] == baseline["analysis"]["data"]["kelly"]["value"]
    assert changed["analysis"]["data"]["kelly"]["value"] != baseline["analysis"]["data"]["kelly"]["value"]
