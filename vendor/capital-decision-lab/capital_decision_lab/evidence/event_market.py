"""Deterministic analysis of user-verified event-market snapshots."""

from __future__ import annotations

import math
from datetime import datetime

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash

from .common import atom, clamp
from .validation import update_eligibility


def _probabilities(snapshot: dict) -> list[float]:
    values = [float(item["probability"]) for item in snapshot.get("outcomes", [])]
    if len(values) < 2 or any(value < 0 or value > 1 for value in values):
        raise ValueError("EVENT_PROBABILITY_INVALID")
    if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError("EVENT_PROBABILITIES_MUST_SUM_TO_ONE")
    return values


def event_market_metrics(snapshot: dict) -> dict[str, float]:
    probabilities = sorted(_probabilities(snapshot), reverse=True)
    consensus = probabilities[0]
    surprise = 1.0 - consensus
    top_two_gap = consensus - probabilities[1]
    entropy = -sum(p * math.log(p) for p in probabilities if p > 0) / math.log(len(probabilities))
    volume = max(0.0, float(snapshot.get("total_volume", 0.0)))
    volume_score = clamp(math.log10(volume + 1.0) / 6.0)
    outcome_volume_score = sum("volume" in item for item in snapshot["outcomes"]) / len(snapshot["outcomes"])
    verification_score = 1.0 if snapshot.get("verification_status") in {"auto_retrieved", "user_verified", "user_corrected"} else 0.0
    liquidity = clamp(
        0.35 * volume_score
        + 0.20 * outcome_volume_score
        + 0.15 * float(bool(snapshot.get("bid_ask_available")))
        + 0.10 * float(bool(snapshot.get("spread_available")))
        + 0.20 * verification_score
    )
    proximity = 0.0
    if snapshot.get("event_date"):
        try:
            event_date = datetime.fromisoformat(snapshot["event_date"].replace("Z", "+00:00"))
            captured_at = datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
            days = max(0.0, (event_date - captured_at).total_seconds() / 86400.0)
            proximity = 1.0 / (1.0 + days / 30.0)
        except (TypeError, ValueError):
            proximity = 0.0
    volatility = clamp((entropy + (1.0 - top_two_gap) + surprise + (1.0 - liquidity) + proximity) / 5.0)
    return {
        "consensus_score": consensus,
        "surprise_probability": surprise,
        "top_two_gap": top_two_gap,
        "normalized_entropy": entropy,
        "event_volatility_score": volatility,
        "market_volume_confidence": liquidity,
    }


def _sum_tag(outcomes: list[dict], *tags: str) -> float:
    expected = set(tags)
    return sum(float(item["probability"]) for item in outcomes if expected.intersection(item.get("tags", [])))


def _domain_metrics(snapshot: dict) -> dict[str, float | dict]:
    outcomes = snapshot["outcomes"]
    domain = snapshot["event_domain"]
    result: dict[str, float | dict] = {}
    if domain == "economy_rates" and all("rate_change_bps" in item for item in outcomes):
        result.update({
            "probability_any_cut": sum(float(x["probability"]) for x in outcomes if x["rate_change_bps"] < 0),
            "probability_no_change": sum(float(x["probability"]) for x in outcomes if x["rate_change_bps"] == 0),
            "probability_any_hike": sum(float(x["probability"]) for x in outcomes if x["rate_change_bps"] > 0),
            "expected_bps_change": sum(float(x["probability"]) * float(x["rate_change_bps"]) for x in outcomes),
        })
        result["rate_tailwind_score"] = result["probability_any_cut"]
        result["rate_headwind_score"] = result["probability_any_hike"]
    elif domain == "geopolitics":
        disruption = _sum_tag(outcomes, "disruption", "shipping_disruption")
        normalization = _sum_tag(outcomes, "normalization", "de_escalation")
        escalation = _sum_tag(outcomes, "escalation")
        result.update({
            "disruption_probability": clamp(disruption),
            "normalization_probability": clamp(normalization),
            "escalation_deescalation_balance": max(-1.0, min(1.0, escalation - normalization)),
            "oil_shock_score": clamp(_sum_tag(outcomes, "oil_shock") or disruption),
            "shipping_disruption_score": clamp(disruption),
            "geopolitical_volatility_score": clamp(disruption + escalation),
        })
    elif domain == "technology":
        actors = {item["actor"]: float(item["probability"]) for item in outcomes if item.get("actor")}
        result.update({
            "actor_leadership_probabilities": actors,
            "technology_leadership_concentration": max(actors.values(), default=0.0),
            "product_release_probability": clamp(_sum_tag(outcomes, "product_release")),
            "regulatory_event_probability": clamp(_sum_tag(outcomes, "regulatory_event")),
            "narrative_momentum_proxy": max((float(item["probability"]) for item in outcomes), default=0.0),
        })
    elif domain == "commodities":
        above = sum(float(x["probability"]) for x in outcomes if x.get("threshold_direction") == "above")
        below = sum(float(x["probability"]) for x in outcomes if x.get("threshold_direction") == "below")
        result.update({
            "probability_above_threshold": above,
            "probability_below_threshold": below,
            "commodity_shock_score": clamp(max(above, below)),
            "risk_off_commodity_signal": clamp(_sum_tag(outcomes, "risk_off")),
        })
    elif domain in {"market_structure", "company_specific"}:
        actors = {item["actor"]: float(item["probability"]) for item in outcomes if item.get("actor")}
        concentration = max(actors.values(), default=max(_probabilities(snapshot)))
        result.update({
            "company_leadership_probabilities": actors,
            "top_company_concentration": concentration,
            "largest_company_market_signal": concentration,
            "ipo_leadership_probability": clamp(_sum_tag(outcomes, "ipo_leadership")),
            "valuation_threshold_probability": clamp(_sum_tag(outcomes, "valuation_threshold")),
        })
    return result


def analyze_event_market(snapshot: dict) -> dict:
    metrics = event_market_metrics(snapshot)
    metrics.update(_domain_metrics(snapshot))
    eligible = update_eligibility(snapshot)
    data = {
        name: atom(value, "calculated", input_refs=[f"snapshot:{snapshot['snapshot_id']}"], formula_ref=f"event_market.{name}")
        for name, value in metrics.items()
    }
    # Direction is intentionally descriptive; thesis direction is supplied later by a sensitivity map.
    data["bullish_pressure"] = atom(0.0, "modeled", limitations=["No universal asset direction is inferred from an event domain."])
    data["bearish_pressure"] = atom(0.0, "modeled", limitations=["No universal asset direction is inferred from an event domain."])
    data["event_evidence_strength"] = atom(
        clamp(metrics["consensus_score"] * metrics["market_volume_confidence"]),
        "modeled", unit="score",
        limitations=["Direction is supplied only by a matching thesis sensitivity rule."],
    )
    impact_channels = sorted({tag for item in snapshot["outcomes"] for tag in item.get("tags", [])})
    document = {
        "contract_version": "nhi.event_market_signal.v1",
        "signal_id": f"event_signal_{canonical_sha256(snapshot)[:16]}",
        "snapshot_ref": {"id": snapshot["snapshot_id"], "canonical_hash": contract_payload_hash(snapshot)},
        "data": data,
        "report_sections": {
            "market_summary": [snapshot["title"], snapshot["event_domain"], snapshot["event_category"]],
            "measured_evidence": ["outcomes", "total_volume", "verification_status"],
            "calculated_signals": sorted(data),
            "forecast_impact_readiness": eligible["eligible"],
            "limitations": ["Event-market confidence is modeled, not truth."],
        },
    }
    document.update({
        "source_type": "polymarket", "event_domain": snapshot["event_domain"],
        "event_category": snapshot["event_category"], "impact_channels": impact_channels,
        "update_eligible": eligible["eligible"], "issues": eligible["issues"],
    })
    document["canonical_hash"] = contract_payload_hash(document)
    return document


analyze_polymarket = analyze_event_market
