"""Deterministic model-implied exposure recommendation engine."""

from __future__ import annotations

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash
from capital_decision_lab.evidence.common import atom, clamp
from capital_decision_lab.host.bridge import analysis_eligibility


_VERIFIED = {"auto_retrieved", "user_verified", "user_corrected"}


def build_recommendation(inputs: dict) -> dict:
    portfolio = inputs["portfolio"]
    current = float(inputs["current_exposure"])
    position_caps = [float(position["max_position_cap"]) for position in portfolio.get("positions", []) if position.get("max_position_cap") is not None]
    limits = [float(inputs["kelly_implied_exposure"]), float(inputs["fractional_kelly"]), float(inputs["exposure_cap"]), *position_caps]
    implied = max(0.0, min(limits))
    portfolio_verified = portfolio.get("verification_status") in _VERIFIED
    host_extractions = inputs.get("host_extractions", [])
    host_evidence_usable = all(analysis_eligibility(bundle.get("extraction", {}))["eligible"] for bundle in host_extractions)
    update_approved = inputs.get("belief_update_status") == "approved"
    health = inputs["model_health"]["state"]
    quality = clamp(inputs.get("evidence_quality", 0.0))
    reason_codes: list[str] = []

    power_law_result = inputs.get("power_law_result")
    heavy_tail_veto: str | None = None
    if isinstance(power_law_result, dict):
        data = power_law_result.get("data", {})
        alpha_atom = data.get("alpha", {})
        prov = alpha_atom.get("provenance_class")
        if prov == "unavailable":
            heavy_tail_veto = "HEAVY_TAIL_FIT_UNAVAILABLE"
        else:
            alpha_val = alpha_atom.get("value")
            if isinstance(alpha_val, (int, float)) and not isinstance(alpha_val, bool):
                if alpha_val <= 2.0:
                    heavy_tail_veto = "HEAVY_TAIL_UNDEFINED_MEAN"
                elif 2.0 < alpha_val <= 3.0:
                    reason_codes.append("HEAVY_TAIL_INFINITE_VARIANCE_ALLOWED")

    if not host_evidence_usable:
        kind, target = "pause", current
        reason_codes.append("HOST_EVIDENCE_CONFIRMATION_REQUIRED")
    elif not portfolio_verified:
        kind, target = "pause", current
        reason_codes.append("PORTFOLIO_VERIFICATION_REQUIRED")
    elif not update_approved:
        kind, target = "hold", current
        reason_codes.append("BELIEF_UPDATE_NOT_APPROVED")
    elif inputs.get("margin_breach") or float(inputs.get("margin_buffer", 0.0)) <= 0:
        kind, target = "avoid_margin", min(current, implied)
        reason_codes.append("MARGIN_OVERRIDE")
    elif health in {"broken", "unavailable"}:
        kind, target = "pause", current
        reason_codes.append("MODEL_HEALTH_BLOCK")
    elif health == "degrading":
        kind, target = "decrease_exposure", min(current, implied)
        reason_codes.append("MODEL_HEALTH_DEGRADING")
    elif heavy_tail_veto is not None and implied > current:
        kind, target = "watch", current
        reason_codes.append(heavy_tail_veto)
    elif float(inputs.get("evidence_contradiction", 0.0)) >= 0.7:
        kind, target = "watch", current
        reason_codes.append("EVIDENCE_CONTRADICTION")
    elif quality < 0.4:
        kind, target = "watch", current
        reason_codes.append("EVIDENCE_QUALITY_WEAK")
    elif implied > current and float(inputs.get("convexity_score", 0.0)) >= 0.5:
        kind, target = "increase_exposure", implied
        reason_codes.extend(["KELLY_ABOVE_CURRENT", "CONVEXITY_SUPPORTIVE"])
    elif implied < current:
        kind, target = "trim_to_kelly", implied
        reason_codes.append("KELLY_BELOW_CURRENT")
    else:
        kind, target = "hold", current
        reason_codes.append("EXPOSURE_ALIGNED")
    hashes = inputs["hashes"]
    intents = sorted({position.get("user_intent") for position in portfolio.get("positions", []) if position.get("user_intent")})
    reason_codes.extend(f"USER_INTENT_{intent.upper()}" for intent in intents)
    document = {
        "contract_version": "nhi.recommendation.v1",
        "recommendation_id": f"recommendation_{canonical_sha256([inputs['case_id'], current, implied, kind])[:16]}",
        "case_id": inputs["case_id"],
        "portfolio_snapshot_hash": hashes["portfolio_snapshot"],
        "belief_state_hash": hashes["belief_state"], "evidence_synthesis_hash": hashes["evidence_synthesis"],
        "kelly_analysis_hash": hashes["kelly_analysis"], "convexity_analysis_hash": hashes["convexity_analysis"],
        "margin_analysis_hash": hashes["margin_analysis"], "model_health_hash": inputs["model_health"]["canonical_hash"],
        "recommendation_type": kind,
        "model_implied_action": kind.replace("_", " "),
        "target_exposure": atom(target, "forecast", unit="capital fraction", input_refs=[hashes["kelly_analysis"]]),
        "current_exposure": atom(current, "measured", unit="capital fraction", input_refs=[hashes["portfolio_snapshot"]]),
        "exposure_delta": atom(target - current, "calculated", unit="capital fraction", input_refs=[hashes["portfolio_snapshot"], hashes["kelly_analysis"]]),
        "reason_codes": reason_codes,
        "kelly_reason": atom("Kelly-implied exposure is above current exposure" if implied > current else "Kelly-implied exposure is at or below current exposure", "modeled"),
        "convexity_reason": atom("convexity is supportive" if float(inputs.get("convexity_score", 0.0)) >= 0.5 else "convexity is weak", "modeled"),
        "margin_reason": atom("margin danger overrides sizing" if inputs.get("margin_breach") or float(inputs.get("margin_buffer", 0.0)) <= 0 else "margin buffer is acceptable under supplied inputs", "modeled"),
        "evidence_reason": atom("host evidence is source-extracted and usable" if host_extractions and host_evidence_usable else "no host extraction was supplied" if not host_extractions else "host evidence requires confirmation", "modeled"),
        "model_health_reason": atom(f"model health is {health}", "modeled"),
        "confidence": atom(quality * (1.0 if health == "healthy" else 0.8), "modeled", unit="score"),
        "limitations": ["Model-implied action under supplied assumptions and retrieved or verified evidence."],
        "required_user_authorization": True,
    }
    document["canonical_hash"] = contract_payload_hash(document)
    return document
