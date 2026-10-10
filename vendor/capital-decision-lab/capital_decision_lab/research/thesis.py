"""Human-confirmed structuring of freeform stock theses."""

from __future__ import annotations

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash


def structure_thesis(*, target_ticker: str, thesis_text: str, time_horizon: str) -> dict:
    """Preserve supplied text while leaving financial assumptions explicitly pending."""
    document = {
        "contract_version": "nhi.stock_thesis.v1",
        "thesis_id": f"thesis_{canonical_sha256([target_ticker, thesis_text, time_horizon])[:16]}",
        "target_ticker": target_ticker, "time_horizon": time_horizon,
        "user_thesis_text": thesis_text, "bear_case": None, "base_case": None,
        "bull_case": None, "moonshot_case": None, "probabilities": None, "payoffs": None,
        "key_catalysts": [], "kill_conditions": [], "margin_constraints": {},
        "max_exposure_cap": None, "confidence_level": None, "confirmation_status": "pending",
    }
    document["canonical_hash"] = contract_payload_hash(document)
    return document
