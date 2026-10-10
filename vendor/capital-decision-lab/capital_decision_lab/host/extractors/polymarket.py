"""Normalize a Host-neutral result into an event-market snapshot."""

from __future__ import annotations

from .common import extraction_bundle, response_fields


def _domain(title: str, fields: dict) -> str:
    explicit = fields.get("event_domain")
    allowed = {"economy_rates", "geopolitics", "technology", "commodities", "market_structure", "company_specific", "index_market_level", "regulation_policy", "other"}
    if explicit in allowed:
        return explicit
    text = title.casefold()
    groups = (
        ("economy_rates", ("fed", "rate", "inflation", "recession")),
        ("geopolitics", ("war", "peace", "iran", "hormuz", "shipping")),
        ("technology", ("ai", "model", "gpt", "claude", "waymo")),
        ("commodities", ("oil", "wti", "gold", "silver")),
        ("market_structure", ("largest company", "ipo", "market cap")),
        ("regulation_policy", ("regulation", "policy", "ban")),
        ("index_market_level", ("s&p", "nasdaq", "index")),
    )
    return next((domain for domain, terms in groups if any(term in text for term in terms)), "other")


def extract_polymarket(response: dict) -> dict:
    fields, status = response_fields(response)
    title = str(fields.get("market_title", fields.get("title", ""))).strip()
    outcomes = fields.get("outcomes")
    if not title or not isinstance(outcomes, list) or len(outcomes) < 2:
        raise ValueError("POLYMARKET_REQUIRED_FIELDS_MISSING")
    document = {
        "contract_version": "nhi.event_market_snapshot.v1",
        "snapshot_id": f"host_{response['response_id']}", "source_type": "polymarket",
        "verification_status": status, "title": title, "event_domain": _domain(title, fields),
        "event_category": str(fields.get("event_category", "other")),
        "captured_at": response["retrieval_timestamp"], "outcomes": outcomes,
        "total_volume": float(fields.get("total_volume", 0.0)),
        "resolution_rules": str(fields.get("resolution_rules", "Unavailable from source extraction")),
    }
    if fields.get("resolution_date"):
        document["event_date"] = str(fields["resolution_date"])
    return extraction_bundle(response, "polymarket", fields, document)
