"""Local deterministic X/Twitter and Reddit evidence analysis."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash

from .common import atom, clamp
from .validation import update_eligibility


_DIRECTION = {"bullish": 1.0, "bearish": -1.0, "mixed": 0.0, "neutral": 0.0, "unknown": 0.0}


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _recency(item: dict) -> float:
    try:
        age = max(0.0, (_timestamp(item["captured_at"]) - _timestamp(item["timestamp"])).total_seconds() / 86400.0)
    except (KeyError, TypeError, ValueError):
        return 0.5
    return 1.0 / (1.0 + age / 7.0)


def _claim_key(item: dict) -> tuple[str, ...]:
    tags = tuple(sorted(str(tag).casefold() for tag in item.get("claim_tags", [])))
    return tags or (str(item.get("content", item.get("post_text", item.get("comment_text", "")))).casefold(),)


def _weighted_direction(items: list[dict], weight) -> float:
    weights = [max(0.0, float(weight(item))) for item in items]
    denominator = sum(weights)
    if denominator == 0:
        return 0.0
    return sum(_DIRECTION.get(item.get("direction"), 0.0) * value for item, value in zip(items, weights)) / denominator


def analyze_social(batch: dict) -> dict:
    source = batch.get("source_type")
    if source not in {"x_twitter", "reddit"}:
        raise ValueError("SOCIAL_SOURCE_UNSUPPORTED")
    eligibility = update_eligibility(batch)
    items = [item for item in batch.get("items", []) if item.get("verification_status", batch.get("verification_status")) in {"auto_retrieved", "user_verified", "user_corrected"}]
    counts = Counter(item.get("direction", "unknown") for item in items)
    count = len(items)
    denominator = count or 1
    net = sum(_DIRECTION.get(item.get("direction"), 0.0) for item in items) / denominator
    claim_counts = Counter(_claim_key(item) for item in items)
    duplicate_count = sum(value - 1 for value in claim_counts.values() if value > 1)
    credibility = sum(clamp(item.get("source_credibility", 0.0)) for item in items) / denominator
    relevance = sum(clamp(item.get("thesis_relevance", 0.0)) for item in items) / denominator
    recency_score = _weighted_direction(items, _recency)
    credibility_score = _weighted_direction(items, lambda item: clamp(item.get("source_credibility", 0.0)))
    data = {
        "evidence_item_count": atom(count, "calculated", unit="items"),
        "bullish_count": atom(counts["bullish"], "calculated", unit="items"),
        "bearish_count": atom(counts["bearish"], "calculated", unit="items"),
        "mixed_count": atom(counts["mixed"], "calculated", unit="items"),
        "neutral_count": atom(counts["neutral"], "calculated", unit="items"),
        "bullish_ratio": atom(counts["bullish"] / denominator, "calculated", unit="ratio"),
        "bearish_ratio": atom(counts["bearish"] / denominator, "calculated", unit="ratio"),
        "net_directional_score": atom(net, "calculated", unit="score"),
        "duplicate_claim_count": atom(duplicate_count, "calculated", unit="items"),
        "recency_weighted_signal_score": atom(recency_score, "calculated", unit="score"),
        "credibility_weighted_signal_score": atom(credibility_score, "calculated", unit="score"),
    }
    if source == "x_twitter":
        diversity = len({item.get("author_handle") for item in items if item.get("author_handle")}) / denominator
        engagement = _weighted_direction(items, lambda item: float(item.get("likes", 0)) + 2 * float(item.get("reposts", 0)) + float(item.get("replies", 0)) + float(item.get("bookmarks", 0)) + float(item.get("views", 0)) / 1000)
        crowding = clamp(duplicate_count / denominator + max(0.0, abs(engagement) - diversity) / 2.0)
        noise = clamp((1.0 - credibility) * 0.6 + duplicate_count / denominator * 0.4)
        data.update({
            "engagement_weighted_directional_score": atom(engagement, "calculated", unit="score"),
            "source_diversity_score": atom(diversity, "calculated", unit="score"),
            "narrative_momentum_score": atom(clamp(abs(engagement) * credibility * relevance), "modeled", unit="score"),
            "crowding_risk_score": atom(crowding, "modeled", unit="score"),
            "noise_penalty": atom(noise, "modeled", unit="score"),
        })
        impact_channels = ["narrative_momentum", "crowding"]
    else:
        diversity = len({item.get("subreddit") for item in items if item.get("subreddit")}) / denominator
        upvote = _weighted_direction(items, lambda item: max(0.0, float(item.get("score", item.get("upvotes", 0)))))
        disagreement = 2.0 * min(counts["bullish"], counts["bearish"]) / denominator
        echo = sum(clamp(item.get("echo_chamber_risk", 0.0)) for item in items) / denominator
        noise = clamp((1.0 - credibility) * 0.5 + echo * 0.3 + duplicate_count / denominator * 0.2)
        data.update({
            "upvote_weighted_directional_score": atom(upvote, "calculated", unit="score"),
            "subreddit_diversity_score": atom(diversity, "calculated", unit="score"),
            "disagreement_score": atom(disagreement, "calculated", unit="score"),
            "echo_chamber_risk_score": atom(echo, "modeled", unit="score"),
            "noise_penalty": atom(noise, "modeled", unit="score"),
            "crowding_risk_score": atom(echo, "modeled", unit="score"),
        })
        impact_channels = ["retail_conviction", "crowding"]
    quality = clamp(credibility * relevance * (1.0 - data["noise_penalty"]["value"]))
    evidence_weight = quality if eligibility["eligible"] else 0.0
    data.update({
        "evidence_weight": atom(evidence_weight, "modeled", unit="score"),
        "bullish_pressure": atom(clamp(max(0.0, net) * evidence_weight), "modeled", unit="score"),
        "bearish_pressure": atom(clamp(max(0.0, -net) * evidence_weight), "modeled", unit="score"),
    })
    document = {
        "contract_version": "nhi.social_evidence_signal.v1",
        "signal_id": f"social_signal_{canonical_sha256(batch)[:16]}",
        "batch_ref": {"id": batch["batch_id"], "canonical_hash": contract_payload_hash(batch)},
        "source_type": source,
        "data": data,
        "report_sections": {
            "source_summary": [source, count], "measured_evidence": [item.get("item_id") for item in items],
            "calculated_signals": sorted(data), "limitations": ["Social evidence is noisy and does not directly change exposure."],
        },
    }
    document.update({
        "event_domain": batch.get("event_domain", "other"), "event_category": batch.get("event_category", "social_evidence"),
        "impact_channels": impact_channels, "update_eligible": eligibility["eligible"], "issues": eligibility["issues"],
    })
    document["canonical_hash"] = contract_payload_hash(document)
    return document
