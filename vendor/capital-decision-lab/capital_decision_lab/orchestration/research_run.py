"""Host-neutral position research workflow over existing deterministic engines."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.evidence.bayesian import build_belief_update
from capital_decision_lab.evidence.event_market import analyze_event_market
from capital_decision_lab.evidence.proposals import apply_approved_proposal
from capital_decision_lab.evidence.social import analyze_social
from capital_decision_lab.evidence.synthesis import synthesize_evidence
from capital_decision_lab.host.bridge import analysis_eligibility, extract_source
from capital_decision_lab.host.confirmation_queue import apply_confirmation_responses, build_confirmation_queue
from capital_decision_lab.orchestration.analyze import analyze_case
from capital_decision_lab.recommendation.engine import build_recommendation
from capital_decision_lab.recommendation.health import evaluate_model_health


REPORT_SECTIONS = (
    "portfolio_summary", "thesis_summary", "evidence_gathered",
    "evidence_requiring_confirmation", "measured_calculated_modeled_forecast",
    "bayesian_belief_update", "kelly_impact", "convexity_impact",
    "margin_safety", "model_health", "recommendation", "required_user_action",
)

MINI_LOOPS = {
    "portfolio": "I need your current portfolio snapshot. Upload a screenshot, paste a table, or import a CSV.",
    "thesis": "I need your bull/base/bear scenario assumptions before I can calculate Kelly.",
    "margin": "I can calculate Kelly and convexity, but margin safety is blocked. Provide borrowed amount, maintenance requirement, and current price.",
    "confirmation": "I extracted fields from your screenshot. Confirm or edit them before I use them.",
    "contradiction": "Polymarket and social evidence conflict. Choose whether macro evidence, narrative momentum, or margin safety should carry more weight.",
}


def _source_type(document: dict, path: Path) -> str | None:
    explicit = document.get("source_type") or document.get("payload", {}).get("source_type")
    if explicit in {"polymarket", "x_twitter", "reddit", "portfolio", "broker_margin", "manual_note"}:
        return explicit
    text = f"{path.name} {document.get('source_url', '')}".casefold()
    aliases = (("polymarket", "polymarket"), ("x_twitter", "twitter"), ("x_twitter", "x.com"),
               ("reddit", "reddit"), ("broker_margin", "margin"), ("portfolio", "portfolio"),
               ("manual_note", "note"))
    return next((source for source, token in aliases if token in text), None)


def _load_host_inputs(folder: Path) -> tuple[list[dict], list[str], list[dict]]:
    bundles: list[dict] = []
    detected: list[str] = []
    issues: list[dict] = []
    for path in sorted(folder.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            issues.append({"code": "HOST_INPUT_INVALID", "path": path.name})
            continue
        if not isinstance(document, dict):
            issues.append({"code": "HOST_INPUT_INVALID", "path": path.name})
            continue
        if document.get("contract_version") == "nhi.confirmation_response.v1":
            continue
        if "extraction" in document and "document" in document:
            bundle = document
            source = bundle["extraction"].get("source_type") or bundle["document"].get("source_type")
        else:
            source = _source_type(document, path)
            if source is None:
                issues.append({"code": "HOST_SOURCE_UNDETECTED", "path": path.name})
                continue
            extracted = extract_source(source, document)
            if extracted["status"] != "ok":
                issues.extend(extracted.get("issues", []))
                continue
            bundle = extracted["extraction_bundle"]
        bundles.append(bundle)
        if source:
            detected.append(source)
    return bundles, sorted(set(detected)), issues


def _load_confirmation_responses(folder: Path) -> list[dict]:
    responses = []
    for path in sorted(folder.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(document, dict) and document.get("contract_version") == "nhi.confirmation_response.v1":
            responses.append(document)
    return responses


def _pending_queue(queue: dict, unresolved_ids: list[str]) -> dict:
    result = copy.deepcopy(queue)
    result["requests"] = [item for item in queue["requests"] if item["request_id"] in unresolved_ids]
    result["pending_count"] = len(result["requests"])
    result["canonical_hash"] = contract_payload_hash(result)
    return result


def _confirmation_report(portfolio: dict, thesis: dict, bundles: list[dict], queue: dict) -> dict:
    return {
        "portfolio_summary": portfolio, "thesis_summary": thesis,
        "evidence_gathered": [bundle["extraction"] for bundle in bundles],
        "evidence_requiring_confirmation": queue["requests"],
        "measured_calculated_modeled_forecast": {}, "bayesian_belief_update": {"status": "blocked"},
        "kelly_impact": {}, "convexity_impact": {}, "margin_safety": {}, "model_health": {"status": "blocked"},
        "recommendation": None,
        "required_user_action": {"prompt": "Confirm, edit, discard, or defer?", "remaining_confirmations": queue["pending_count"]},
    }


def _atom_value(analysis: dict, name: str, default: Any = None) -> Any:
    atom = analysis.get("data", {}).get(name, {})
    return atom.get("value", default) if isinstance(atom, dict) else default


def _sync_approved_stock_input(case: dict, proposal: dict) -> dict:
    updated = apply_approved_proposal(case, proposal)
    if proposal.get("approval_status") != "approved":
        return updated
    proposed = proposal.get("proposed_assumption", {})
    name = proposed.get("name")
    stock_atom = updated.get("inputs", {}).get("kelly_stock")
    if name in {"win_probability", "net_odds", "confidence", "kelly_fraction", "exposure_cap"} and isinstance(stock_atom, dict) and isinstance(stock_atom.get("value"), dict):
        stock_atom["value"][name] = proposed.get("value")
        if name == "win_probability":
            stock_atom["value"]["loss_probability"] = 1.0 - float(proposed.get("value"))
        stock_atom["provenance_class"] = "forecast"
    return updated


def _signals(bundles: list[dict]) -> list[dict]:
    values = []
    for bundle in bundles:
        document = bundle.get("document", {})
        source = document.get("source_type")
        if source == "polymarket":
            values.append(analyze_event_market(document))
        elif source in {"x_twitter", "reddit"}:
            values.append(analyze_social(document))
    return values


def _portfolio_from_bundles(bundles: list[dict]) -> dict | None:
    return next((bundle["document"] for bundle in bundles if bundle.get("document", {}).get("contract_version") == "nhi.portfolio_snapshot.v1"), None)


def _report(portfolio: dict, thesis: dict, bundles: list[dict], synthesis: dict, belief_update: dict | None,
            analysis: dict, health: dict, recommendation: dict) -> dict:
    pending = [bundle["extraction"] for bundle in bundles if not analysis_eligibility(bundle.get("extraction", {}))["eligible"]]
    return {
        "portfolio_summary": portfolio,
        "thesis_summary": thesis,
        "evidence_gathered": [bundle["extraction"] for bundle in bundles],
        "evidence_requiring_confirmation": pending,
        "measured_calculated_modeled_forecast": analysis["data"],
        "bayesian_belief_update": belief_update or {"status": "unavailable due to insufficient inputs"},
        "kelly_impact": {name: analysis["data"][name] for name in ("full_kelly_fraction", "fractional_kelly_reference", "capped_exposure")},
        "convexity_impact": {name: analysis["data"][name] for name in ("convexity_score", "upside_downside_multiple", "convexity_expected_return")},
        "margin_safety": {name: analysis["data"][name] for name in ("current_margin_ratio", "liquidation_buffer_percent", "margin_warning")},
        "model_health": health,
        "recommendation": recommendation,
        "required_user_action": {"authorization_required": True, "status": "pending_user_authorization"},
    }


def run_analyze_position(case_bundle: dict, host_inputs: Path) -> dict:
    """Run the local workflow; never authorize or write a decision record."""
    host_inputs = Path(host_inputs)
    bundles, detected, issues = _load_host_inputs(host_inputs)
    portfolio = case_bundle.get("portfolio") or _portfolio_from_bundles(bundles)
    if portfolio is None:
        return {"status": "blocked_missing_portfolio", "mini_loop": MINI_LOOPS["portfolio"], "issues": issues, "recommendation": None}
    thesis = case_bundle.get("thesis")
    if not thesis or thesis.get("confirmation_status") != "confirmed" or not thesis.get("probabilities") or not thesis.get("payoffs"):
        return {"status": "blocked_missing_thesis", "mini_loop": MINI_LOOPS["thesis"], "issues": issues, "recommendation": None}
    decision_case = copy.deepcopy(case_bundle.get("decision_case", case_bundle))
    if not isinstance(decision_case.get("inputs", {}).get("margin_inputs", {}).get("value"), dict):
        return {"status": "blocked_missing_margin", "mini_loop": MINI_LOOPS["margin"], "issues": issues, "recommendation": None}
    pending = [bundle for bundle in bundles if not analysis_eligibility(bundle.get("extraction", {}))["eligible"]]
    pairing = None
    if pending:
        queue = build_confirmation_queue(decision_case["case_id"], pending)
        responses = _load_confirmation_responses(host_inputs)
        if responses:
            try:
                applied = apply_confirmation_responses(queue, responses, bundles)
            except ValueError as exc:
                return {"status": "blocked_confirmation_invalid", "mini_loop": "I need confirmation before using this evidence.", "issues": [{"code": str(exc)}], "confirmation_queue": queue, "detected_source_types": detected, "recommendation": None}
            bundles = applied["bundles"]
            pairing = applied["pairing"]
            if applied["unresolved_count"]:
                queue = _pending_queue(queue, pairing["unresolved_request_ids"])
                return {"status": "blocked_confirmation_required", "mini_loop": MINI_LOOPS["confirmation"], "issues": [], "confirmation_queue": queue, "confirmation_pairing": pairing, "detected_source_types": detected, "recommendation": None, "report": _confirmation_report(portfolio, thesis, bundles, queue)}
        else:
            return {"status": "blocked_confirmation_required", "mini_loop": MINI_LOOPS["confirmation"], "issues": [{"code": "HOST_EXTRACTION_CONFIRMATION_REQUIRED"}], "confirmation_queue": queue, "detected_source_types": detected, "recommendation": None, "report": _confirmation_report(portfolio, thesis, bundles, queue)}

    signals = _signals(bundles)
    synthesis = synthesize_evidence(signals)
    belief_update = None
    if case_bundle.get("belief") and case_bundle.get("sensitivity_map"):
        belief_update = build_belief_update(case_bundle["belief"], synthesis, case_bundle["sensitivity_map"])
    proposal = case_bundle.get("assumption_update", {"approval_status": "pending"})
    analyzed_case = _sync_approved_stock_input(decision_case, proposal)
    analysis = analyze_case(analyzed_case)
    contradiction = float(synthesis["data"]["contradiction_score"]["value"])
    quality = float(synthesis["data"]["evidence_quality_score"]["value"])
    margin_buffer = _atom_value(analysis, "liquidation_buffer_percent", 0.0)
    margin_rows = _atom_value(analysis, "margin_stress_table", []) or []
    margin_breach = any(row.get("maintenance_breach") for row in margin_rows)
    health = evaluate_model_health(
        contradiction=contradiction, edge_compression=0.0, drawdown_ratio=0.0,
        margin_stress=1.0 if margin_breach or margin_buffer <= 0 else 0.0,
        kill_condition_triggered=False, confidence=quality or 0.01, staleness=0.0,
    )
    position = next((item for item in portfolio.get("positions", []) if item.get("ticker") == thesis.get("target_ticker")), portfolio.get("positions", [{}])[0])
    kelly = _atom_value(analysis, "capped_exposure", _atom_value(analysis, "capped_fractional_kelly", 0.0)) or 0.0
    fractional = _atom_value(analysis, "fractional_kelly_reference", _atom_value(analysis, "fractional_kelly", kelly)) or 0.0
    cap = analyzed_case.get("inputs", {}).get("exposure_cap", {}).get("value", 1.0)
    recommendation_inputs = {
        "case_id": analyzed_case["case_id"], "portfolio": portfolio,
        "current_exposure": position.get("position_weight", 0.0), "kelly_implied_exposure": kelly,
        "fractional_kelly": fractional, "exposure_cap": cap,
        "convexity_score": _atom_value(analysis, "convexity_score", 0.0) or 0.0,
        "margin_buffer": margin_buffer, "margin_breach": margin_breach,
        "model_health": health, "evidence_quality": quality,
        "evidence_contradiction": contradiction, "belief_update_status": proposal.get("approval_status", "pending"),
        "host_extractions": bundles,
        "hashes": {"portfolio_snapshot": contract_payload_hash(portfolio),
                   "belief_state": contract_payload_hash(case_bundle.get("belief", {"status": "unavailable"})),
                   "evidence_synthesis": synthesis["canonical_hash"], "kelly_analysis": analysis["canonical_hash"],
                   "convexity_analysis": analysis["canonical_hash"], "margin_analysis": analysis["canonical_hash"]},
    }
    recommendation = build_recommendation(recommendation_inputs)
    report = _report(portfolio, thesis, bundles, synthesis, belief_update, analysis, health, recommendation)
    mini_loop = MINI_LOOPS["contradiction"] if recommendation["recommendation_type"] == "watch" and contradiction >= 0.7 else None
    return {"status": "ok", "issues": issues, "detected_source_types": detected, "analysis": analysis,
            "evidence_synthesis": synthesis, "belief_update": belief_update, "recommendation": recommendation,
            "decision_record": {"status": "pending_user_authorization", "recommendation_hash": recommendation["canonical_hash"]},
            "report": report, "mini_loop": mini_loop, "confirmation_pairing": pairing}
