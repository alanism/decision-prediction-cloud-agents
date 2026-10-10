from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.orchestration.research_run import REPORT_SECTIONS, _load_host_inputs, run_analyze_position
from capital_decision_lab.plugin.commands import run_cli


def atom(value):
    return {"value": value, "provenance_class": "assumed"}


def workflow_case(*, portfolio=True, thesis=True, margin=True, approval="approved") -> dict:
    decision_case = {
        "contract_version": "nhi.decision_case.v1", "case_id": "case_workflow",
        "title": "Synthetic position review", "inputs": {
            "win_probability": atom(0.65), "net_odds": atom(1.5), "kelly_fraction": atom(0.5),
            "exposure_cap": atom(0.6), "kelly_stock": atom({"capital_at_risk": 10000, "win_probability": 0.65, "win_payoff_multiple": 1.5, "loss_probability": 0.35, "loss_payoff_multiple": -1.0, "kelly_fraction": 0.5, "max_exposure_cap": 0.6, "confidence_haircut": 0.8}),
            "convexity_scenarios": atom({"scenarios": [{"name": "bear", "probability": 0.25, "payoff": -2000, "return": -0.4}, {"name": "base", "probability": 0.35, "payoff": 500, "return": 0.1}, {"name": "bull", "probability": 0.4, "payoff": 4000, "return": 0.8}]}),
        }, "alternatives": [],
    }
    result = {"decision_case": decision_case, "assumption_update": {"approval_status": approval, "proposal_id": "proposal_default", "bayesian_update_hash": "c" * 64, "proposed_assumption": {"name": "win_probability", "value": 0.65}}}
    if portfolio:
        result["portfolio"] = {"contract_version": "nhi.portfolio_snapshot.v1", "snapshot_id": "portfolio_1", "capture_timestamp": "2026-07-04T00:00:00Z", "cash": 6000, "total_equity": 10000, "margin_used": 0, "borrowed_amount": 0, "maintenance_margin_requirement": 0.25, "initial_margin_requirement": 0.5, "portfolio_source": "manual", "verification_status": "user_verified", "positions": [{"ticker": "SYNTH", "shares": 40, "current_price": 100, "market_value": 4000, "position_weight": 0.4, "user_intent": "hold", "max_position_cap": 0.6}]}
        if margin:
            decision_case["inputs"]["margin_inputs"] = atom({"cash_equity": 6000, "position_market_value": 4000, "borrowed_amount": 0, "maintenance_margin_requirement": 0.25, "initial_margin_requirement": 0.5, "current_price": 100, "shares": 40, "stress_price_declines": [0.2, 0.5]})
    if thesis:
        result["thesis"] = {"target_ticker": "SYNTH", "time_horizon": "18 months", "user_thesis_text": "Synthetic supplied thesis", "probabilities": {"bear": 0.25, "base": 0.35, "bull": 0.4}, "payoffs": {"bear": -0.4, "base": 0.1, "bull": 0.8}, "confirmation_status": "confirmed"}
    return result


def response(source: str, fields: dict, method="browser") -> dict:
    value = {"contract_version": "nhi.host_capability_response.v1", "response_id": f"response_{source}", "request_ref": {"request_id": "request_1", "canonical_hash": "a" * 64}, "capability": "screenshot_ocr" if method == "screenshot" else "browser_extract_selection", "status": "ok", "retrieval_method": method, "retrieval_timestamp": "2026-07-04T00:00:00Z", "source_url": f"https://example.invalid/{source}", "raw_content_hash": "b" * 64, "payload": {"source_type": source, "extracted_fields": fields}, "confidence": 0.9, "limitations": []}
    value["canonical_hash"] = contract_payload_hash(value)
    return value


def write_inputs(folder: Path, documents: list[dict]) -> None:
    folder.mkdir()
    for index, document in enumerate(documents):
        (folder / f"input-{index}.json").write_text(json.dumps(document), encoding="utf-8")


def social_fields(direction="bullish") -> dict:
    return {"author_handle": "source", "post_text": "Supplied observation", "timestamp": "2026-07-04T00:00:00Z", "direction_candidate": direction, "source_credibility": 0.9, "thesis_relevance": 0.9, "likes": 20}


def test_loads_inputs_detects_sources_and_builds_complete_pending_report(tmp_path: Path) -> None:
    folder = tmp_path / "host"; write_inputs(folder, [response("x_twitter", social_fields()), response("manual_note", {"text": "User supplied note"}, "manual")])
    result = run_analyze_position(workflow_case(), folder)
    assert result["status"] == "ok"
    assert result["detected_source_types"] == ["manual_note", "x_twitter"]
    assert set(result["report"]) == set(REPORT_SECTIONS)
    assert result["decision_record"]["status"] == "pending_user_authorization"
    assert result["recommendation"]["required_user_authorization"] is True


def test_each_detected_source_routes_to_its_specific_extractor(tmp_path: Path, monkeypatch) -> None:
    source_types = ["polymarket", "x_twitter", "reddit", "portfolio", "broker_margin", "manual_note"]
    folder = tmp_path / "host"; write_inputs(folder, [response(source, {}) for source in source_types])
    called = []
    def fake_extract(source, document):
        called.append(source)
        return {"status": "ok", "extraction_bundle": {"extraction": {"source_type": source}, "document": {"source_type": source}}}
    monkeypatch.setattr("capital_decision_lab.orchestration.research_run.extract_source", fake_extract)
    _, detected, issues = _load_host_inputs(folder)
    assert issues == []
    assert sorted(called) == sorted(source_types)
    assert detected == sorted(source_types)


def test_unverified_screenshot_blocks_recommendation(tmp_path: Path) -> None:
    folder = tmp_path / "host"; write_inputs(folder, [response("x_twitter", social_fields(), "screenshot")])
    result = run_analyze_position(workflow_case(), folder)
    assert result["status"] == "blocked_confirmation_required"
    assert result["recommendation"] is None
    assert "Confirm or edit" in result["mini_loop"]


def test_approved_update_changes_analysis_but_pending_does_not(tmp_path: Path) -> None:
    folder = tmp_path / "host"; write_inputs(folder, [response("x_twitter", social_fields())])
    approved = workflow_case(approval="approved")
    approved["assumption_update"].update({"proposal_id": "proposal_1", "bayesian_update_hash": "c" * 64, "proposed_assumption": {"name": "win_probability", "value": 0.8}})
    pending = workflow_case(approval="pending"); pending["assumption_update"].update(approved["assumption_update"]); pending["assumption_update"]["approval_status"] = "pending"
    assert run_analyze_position(approved, folder)["analysis"]["data"]["full_kelly_fraction"]["value"] != run_analyze_position(pending, folder)["analysis"]["data"]["full_kelly_fraction"]["value"]


def test_margin_danger_overrides_kelly_and_contradiction_can_watch(tmp_path: Path) -> None:
    folder = tmp_path / "host"; write_inputs(folder, [response("x_twitter", social_fields())])
    case = workflow_case(); margin = case["decision_case"]["inputs"]["margin_inputs"]["value"]; margin.update({"cash_equity": 0, "position_market_value": 10000, "borrowed_amount": 7000, "maintenance_margin_requirement": 0.35, "shares": 100})
    assert run_analyze_position(case, folder)["recommendation"]["recommendation_type"] == "avoid_margin"
    conflicting = tmp_path / "conflicting"; write_inputs(conflicting, [response("x_twitter", social_fields("bullish")), response("reddit", {"subreddit": "source", "thread_title": "Counterpoint", "post_text": "Supplied counterpoint", "timestamp": "2026-07-04T00:00:00Z", "direction_candidate": "bearish", "source_credibility": 1, "thesis_relevance": 1, "score": 50})])
    assert run_analyze_position(workflow_case(), conflicting)["recommendation"]["recommendation_type"] == "watch"


def test_missing_inputs_return_exact_actionable_loops(tmp_path: Path) -> None:
    folder = tmp_path / "host"; write_inputs(folder, [response("manual_note", {"text": "User supplied note"}, "manual")])
    assert run_analyze_position(workflow_case(portfolio=False), folder)["mini_loop"] == "I need your current portfolio snapshot. Upload a screenshot, paste a table, or import a CSV."
    assert run_analyze_position(workflow_case(thesis=False), folder)["mini_loop"] == "I need your bull/base/bear scenario assumptions before I can calculate Kelly."
    assert run_analyze_position(workflow_case(margin=False), folder)["mini_loop"] == "I can calculate Kelly and convexity, but margin safety is blocked. Provide borrowed amount, maintenance requirement, and current price."


def test_cli_alias_and_research_run_share_orchestrator(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    case_path = local / "case.json"; case_path.write_text(json.dumps(workflow_case()), encoding="utf-8")
    folder = local / "host"; write_inputs(folder, [response("x_twitter", social_fields())])
    research_code, research = run_cli(["research", "run", "--case", str(case_path), "--host-inputs", str(folder)], local_root=local)
    alias_code, alias = run_cli(["analyze-position", "--case", str(case_path), "--host-inputs", str(folder)], local_root=local)
    assert (research_code, alias_code) == (0, 0)
    assert research["recommendation"]["canonical_hash"] == alias["recommendation"]["canonical_hash"]


def test_cli_rejects_host_folder_outside_local_root(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    case_path = local / "case.json"; case_path.write_text(json.dumps(workflow_case()), encoding="utf-8")
    outside = tmp_path / "outside"; write_inputs(outside, [response("x_twitter", social_fields())])
    code, result = run_cli(["analyze-position", "--case", str(case_path), "--host-inputs", str(outside)], local_root=local)
    assert code == 2
    assert result["status"] == "failed"
