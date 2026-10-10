"""Model-health classification from explicit deterioration signals."""

from __future__ import annotations

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.evidence.common import atom, clamp


def evaluate_model_health(*, contradiction: float, edge_compression: float, drawdown_ratio: float, margin_stress: float, kill_condition_triggered: bool, confidence: float, staleness: float) -> dict:
    reasons = []
    if contradiction >= 0.7:
        reasons.append("EVIDENCE_CONTRADICTION")
    if edge_compression >= 0.7:
        reasons.append("EDGE_COMPRESSION")
    if drawdown_ratio > 1.0:
        reasons.append("DRAWDOWN_BEYOND_EXPECTED")
    if margin_stress >= 0.6:
        reasons.append("MARGIN_STRESS")
    if confidence < 0.4:
        reasons.append("CONFIDENCE_DECAY")
    if staleness >= 0.7:
        reasons.append("STALE_EVIDENCE")
    score = sum((clamp(contradiction), clamp(edge_compression), clamp(drawdown_ratio / 2.0), clamp(margin_stress), 1.0 - clamp(confidence), clamp(staleness))) / 6.0
    if kill_condition_triggered:
        state = "broken"
        reasons.append("KILL_CONDITION_TRIGGERED")
    elif confidence <= 0:
        state = "unavailable"
    elif score >= 0.6:
        state = "degrading"
    elif score >= 0.3:
        state = "watch"
    else:
        state = "healthy"
    document = {
        "state": state, "reason_codes": reasons,
        "data": {
            "confidence": atom(clamp(confidence) * (1.0 - score), "modeled", unit="score"),
            "impact_on_kelly": atom("reduce modeled confidence" if state in {"degrading", "broken"} else "no health adjustment", "forecast"),
            "impact_on_convexity": atom("retest downside scenarios" if state != "healthy" else "no health adjustment", "forecast"),
            "impact_on_margin_safety": atom("prioritize margin buffer" if margin_stress >= 0.6 else "no health adjustment", "forecast"),
        },
    }
    document["canonical_hash"] = contract_payload_hash(document)
    return document
