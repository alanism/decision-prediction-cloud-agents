from __future__ import annotations

import json
from pathlib import Path

import pytest

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.host.bridge import extract_source
from capital_decision_lab.host.confirmation_queue import apply_confirmation_responses, build_confirmation_queue
from capital_decision_lab.plugin.commands import run_cli
from tests.orchestration.test_analyze_position import response, social_fields, workflow_case, write_inputs


def screenshot_bundle(source="x_twitter") -> dict:
    fields = social_fields() if source == "x_twitter" else {
        "subreddit": "source", "post_text": "Supplied counterpoint",
        "timestamp": "2026-07-04T00:00:00Z", "direction_candidate": "bearish",
    }
    return extract_source(source, response(source, fields, "screenshot"))["extraction_bundle"]


def make_response(request: dict, action="confirm", **overrides) -> dict:
    value = {
        "contract_version": "nhi.confirmation_response.v1",
        "response_id": f"response_{request['request_id']}_{action}",
        "request_id": request["request_id"], "action": action,
        "confirmed_fields": request["extracted_fields"], "corrected_fields": {},
        "created_timestamp": "2026-07-04T01:00:00Z", **overrides,
    }
    value["canonical_hash"] = contract_payload_hash(value)
    return value


def test_queue_contains_source_identity_hash_and_actions() -> None:
    bundle = screenshot_bundle()
    queue = build_confirmation_queue("case_1", [bundle])
    request = queue["requests"][0]
    assert request["source_extraction_id"] == bundle["extraction"]["extraction_id"]
    assert request["source_artifact_hash"] == bundle["extraction"]["raw_content_hash"]
    assert request["allowed_actions"] == ["confirm", "correct", "discard", "defer"]


def test_confirm_and_correct_promote_evidence() -> None:
    bundle = screenshot_bundle(); queue = build_confirmation_queue("case_1", [bundle]); request = queue["requests"][0]
    confirmed = apply_confirmation_responses(queue, [make_response(request)], [bundle])
    assert confirmed["bundles"][0]["extraction"]["verification_status"] == "user_verified"
    corrected = apply_confirmation_responses(queue, [make_response(request, "correct", corrected_fields={"post_text": "Corrected supplied text"})], [bundle])
    assert corrected["bundles"][0]["extraction"]["verification_status"] == "user_corrected"
    assert corrected["bundles"][0]["document"]["items"][0]["post_text"] == "Corrected supplied text"


def test_discard_excludes_and_defer_preserves_but_blocks() -> None:
    bundle = screenshot_bundle(); queue = build_confirmation_queue("case_1", [bundle]); request = queue["requests"][0]
    discarded = apply_confirmation_responses(queue, [make_response(request, "discard", discard_reason="Not relevant")], [bundle])
    assert discarded["bundles"] == [] and discarded["unresolved_count"] == 0
    deferred = apply_confirmation_responses(queue, [make_response(request, "defer")], [bundle])
    assert deferred["bundles"][0] == bundle and deferred["unresolved_count"] == 1


def test_pairing_exact_and_fallback_identifiers() -> None:
    bundle = screenshot_bundle(); queue = build_confirmation_queue("case_1", [bundle]); request = queue["requests"][0]
    exact = apply_confirmation_responses(queue, [make_response(request)], [bundle])
    assert exact["pairing"]["pairs"][0]["match_method"] == "request_id"
    by_extraction = make_response(request, request_id="missing", source_extraction_id=request["source_extraction_id"])
    assert apply_confirmation_responses(queue, [by_extraction], [bundle])["pairing"]["pairs"][0]["match_method"] == "source_extraction_id"
    by_hash = make_response(request, request_id="missing", source_artifact_hash=request["source_artifact_hash"])
    assert apply_confirmation_responses(queue, [by_hash], [bundle])["pairing"]["pairs"][0]["match_method"] == "source_artifact_hash"


def test_ambiguous_and_stale_pairing_are_rejected() -> None:
    first = screenshot_bundle(); second = screenshot_bundle("reddit")
    second["extraction"]["raw_content_hash"] = first["extraction"]["raw_content_hash"]
    second["extraction"]["canonical_hash"] = contract_payload_hash(second["extraction"])
    queue = build_confirmation_queue("case_1", [first, second]); request = queue["requests"][0]
    with pytest.raises(ValueError, match="CONFIRMATION_PAIR_AMBIGUOUS"):
        apply_confirmation_responses(queue, [make_response(request, request_id="missing", source_artifact_hash=request["source_artifact_hash"])], [first, second])
    with pytest.raises(ValueError, match="CONFIRMATION_SOURCE_STALE"):
        apply_confirmation_responses(queue, [make_response(request, source_artifact_hash="f" * 64)], [first])


def test_analyze_position_auto_pairs_and_resumes_or_defers(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir(); case_path = local / "case.json"
    case = workflow_case()
    case["belief"] = {"contract_version": "nhi.belief_state.v1", "belief_id": "belief_1", "case_ref": "case_workflow", "assumption": "win_probability", "prior_probability": 0.65, "canonical_hash": "c" * 64}
    case["sensitivity_map"] = {"contract_version": "nhi.thesis_sensitivity_map.v1", "map_id": "map_1", "target_asset": {"ticker": "SYNTH"}, "canonical_hash": "d" * 64, "sensitivity_rules": [{"source_type": "x_twitter", "event_domain": "other", "event_category": "social_evidence", "impact_channel": "narrative_momentum", "direction_for_thesis": "bullish", "sensitivity": "high", "affected_assumption": "win_probability"}]}
    case_path.write_text(json.dumps(case), encoding="utf-8")
    folder = local / "host"; bundle = screenshot_bundle(); write_inputs(folder, [bundle])
    blocked_code, blocked = run_cli(["analyze-position", "--case", str(case_path), "--host-inputs", str(folder)], local_root=local)
    assert blocked_code == 3 and blocked["confirmation_queue"]["pending_count"] == 1
    request = blocked["confirmation_queue"]["requests"][0]
    (folder / "confirmation.json").write_text(json.dumps(make_response(request)), encoding="utf-8")
    resumed_code, resumed = run_cli(["analyze-position", "--case", str(case_path), "--host-inputs", str(folder)], local_root=local)
    assert resumed_code == 0 and resumed["belief_update"]["contract_version"] == "nhi.bayesian_update.v1"
    assert resumed["report"]["evidence_requiring_confirmation"] == []
    (folder / "confirmation.json").write_text(json.dumps(make_response(request, "defer")), encoding="utf-8")
    defer_code, deferred = run_cli(["analyze-position", "--case", str(case_path), "--host-inputs", str(folder)], local_root=local)
    assert defer_code == 3 and deferred["confirmation_queue"]["pending_count"] == 1
    (folder / "confirmation.json").write_text(json.dumps(make_response(request, "discard", discard_reason="Not relevant")), encoding="utf-8")
    discard_code, discarded = run_cli(["analyze-position", "--case", str(case_path), "--host-inputs", str(folder)], local_root=local)
    assert discard_code == 0 and discarded["evidence_synthesis"]["evidence_refs"] == []


def test_confirmation_cli_queue_apply_and_status(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir(); case = workflow_case()
    case_path = local / "case.json"; case_path.write_text(json.dumps(case), encoding="utf-8")
    host = local / "host"; write_inputs(host, [screenshot_bundle()])
    code, queued = run_cli(["confirmation", "queue", "--case", str(case_path), "--host-inputs", str(host)], local_root=local)
    assert code == 0 and queued["confirmation_queue"]["pending_count"] == 1
    queue_path = local / "queue.json"; queue_path.write_text(json.dumps(queued["confirmation_queue"]), encoding="utf-8")
    responses = local / "responses"; responses.mkdir()
    (responses / "response.json").write_text(json.dumps(make_response(queued["confirmation_queue"]["requests"][0])), encoding="utf-8")
    code, applied = run_cli(["confirmation", "apply", "--queue", str(queue_path), "--responses", str(responses)], local_root=local)
    assert code == 0 and applied["confirmation_pairing"]["unresolved_request_ids"] == []
    case["confirmation_queue"] = queued["confirmation_queue"]
    case_path.write_text(json.dumps(case), encoding="utf-8")
    code, status = run_cli(["confirmation", "status", "--case", str(case_path)], local_root=local)
    assert code == 0 and status["pending_count"] == 1
