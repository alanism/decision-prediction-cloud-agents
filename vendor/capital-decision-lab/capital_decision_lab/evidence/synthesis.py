"""Source-level evidence synthesis without item-count over-weighting."""

from __future__ import annotations

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash

from .common import atom, atom_value, clamp


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def synthesize_evidence(signals: list[dict]) -> dict:
    eligible = [signal for signal in signals if signal.get("update_eligible", True)]
    bullish = [clamp(atom_value(signal, "bullish_pressure")) for signal in eligible]
    bearish = [clamp(atom_value(signal, "bearish_pressure")) for signal in eligible]
    weights = [clamp(atom_value(signal, "market_volume_confidence", atom_value(signal, "evidence_weight", 0.0))) for signal in eligible]
    volatility = [clamp(atom_value(signal, "event_volatility_score", atom_value(signal, "disagreement_score", 0.0))) for signal in eligible]
    crowding = [clamp(atom_value(signal, "crowding_risk_score", 0.0)) for signal in eligible]
    event_strength = [clamp(atom_value(signal, "event_evidence_strength", 0.0)) for signal in eligible]
    source_types = {signal.get("source_type", "other") for signal in eligible}
    source_diversity = len(source_types) / len(eligible) if eligible else 0.0
    bull = _mean(bullish)
    bear = _mean(bearish)
    contradiction = clamp(2.0 * min(bull, bear) + (_mean([abs(b - r) for b, r in zip(bullish, bearish)]) if bullish else 0.0) / 2.0)
    quality = clamp(_mean(weights) * (0.7 + 0.3 * source_diversity))
    direction = "bullish" if bull > bear else "bearish" if bear > bull else "mixed"
    data = {
        "dominant_evidence_direction": atom(direction, "modeled"),
        "source_diversity": atom(clamp(source_diversity), "calculated", unit="score"),
        "contradiction_score": atom(contradiction, "modeled", unit="score"),
        "evidence_quality_score": atom(quality, "modeled", unit="score"),
        "evidence_weight": atom(clamp(quality * (1.0 - contradiction * 0.5)), "modeled", unit="score"),
        "thesis_relevance": atom(quality, "modeled", unit="score"),
        "bullish_pressure": atom(bull, "modeled", unit="score"),
        "bearish_pressure": atom(bear, "modeled", unit="score"),
        "volatility_pressure": atom(max(volatility, default=0.0), "modeled", unit="score"),
        "crowding_pressure": atom(max(crowding, default=0.0), "modeled", unit="score"),
        "event_evidence_strength": atom(max(event_strength, default=0.0), "modeled", unit="score"),
        "confidence": atom(clamp(quality * (1.0 - contradiction)), "modeled", unit="score"),
    }
    document = {
        "contract_version": "nhi.evidence_synthesis.v1",
        "synthesis_id": f"synthesis_{canonical_sha256([s.get('canonical_hash') for s in signals])[:16]}",
        "source_contexts": [{
            "source_type": signal.get("source_type", "other"), "event_domain": signal.get("event_domain", "other"),
            "event_category": signal.get("event_category", "other"), "impact_channels": signal.get("impact_channels", []),
        } for signal in eligible],
        "evidence_refs": [signal.get("signal_id", signal.get("canonical_hash", "unknown")) for signal in eligible],
        "data": data,
        "limitations": ["Source-level aggregation preserves contradictions and discounts unverified evidence."],
    }
    document["canonical_hash"] = contract_payload_hash(document)
    return document
