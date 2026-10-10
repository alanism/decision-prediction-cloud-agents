from __future__ import annotations

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.host.confirmation import apply_confirmation
from capital_decision_lab.host.extractors.broker_margin import extract_broker_margin
from capital_decision_lab.host.extractors.manual_note import extract_manual_note
from capital_decision_lab.host.extractors.polymarket import extract_polymarket
from capital_decision_lab.host.extractors.portfolio_table import extract_portfolio_table
from capital_decision_lab.host.extractors.reddit import extract_reddit
from capital_decision_lab.host.extractors.x_twitter import extract_x_twitter


def response(source: str, fields: dict, *, method: str = "browser", confidence: float = 0.9) -> dict:
    document = {
        "contract_version": "nhi.host_capability_response.v1", "response_id": f"response_{source}",
        "request_ref": {"request_id": "request_1", "canonical_hash": "a" * 64},
        "capability": "screenshot_ocr" if method == "screenshot" else "browser_extract_selection",
        "status": "ok", "retrieval_method": method, "retrieval_timestamp": "2026-07-04T00:00:00Z",
        "source_url": f"https://example.invalid/{source}", "raw_content_hash": "b" * 64,
        "payload": {"extracted_fields": fields}, "confidence": confidence, "limitations": [],
    }
    document["canonical_hash"] = contract_payload_hash(document)
    return document


def test_polymarket_structured_and_screenshot_extraction() -> None:
    fields = {"market_title": "Will rates be cut?", "event_category": "rate_cut", "resolution_date": "2026-08-01", "resolution_rules": "Synthetic rule", "total_volume": 50000, "outcomes": [{"name": "Yes", "probability": 0.6}, {"name": "No", "probability": 0.4}]}
    structured = extract_polymarket(response("market", fields))
    assert structured["document"]["event_domain"] == "economy_rates"
    assert structured["document"]["verification_status"] == "auto_retrieved"
    assert validate_contract(structured["document"]) == []
    screenshot = extract_polymarket(response("market", fields, method="screenshot"))
    assert screenshot["requires_confirmation"] is True
    assert screenshot["document"]["verification_status"] == "unverified_extraction"


def test_low_field_confidence_requires_confirmation() -> None:
    host_response = response("market", {"market_title": "Synthetic market", "resolution_rules": "Rule", "total_volume": 10, "outcomes": [{"name": "Yes", "probability": 0.5}, {"name": "No", "probability": 0.5}]})
    host_response["payload"]["field_confidence"] = {"total_volume": 0.4}
    host_response["canonical_hash"] = contract_payload_hash(host_response)
    result = extract_polymarket(host_response)
    assert result["requires_confirmation"] is True
    assert result["extraction"]["field_confidence"]["total_volume"] == 0.4


def test_x_twitter_url_text_and_screenshot_extraction() -> None:
    fields = {"author_handle": "synthetic_author", "author_display_name": "Synthetic Author", "post_text": "Synthetic product update", "timestamp": "2026-07-04T00:00:00Z", "likes": 20, "reposts": 3, "replies": 2, "views": 1000}
    result = extract_x_twitter(response("post", fields))
    assert result["document"]["source_type"] == "x_twitter"
    assert result["document"]["items"][0]["post_text"] == fields["post_text"]
    assert result["document"]["verification_status"] == "auto_retrieved"
    screenshot = extract_x_twitter(response("post", fields, method="screenshot"))
    assert screenshot["document"]["verification_status"] == "unverified_extraction"


def test_reddit_url_text_and_screenshot_extraction() -> None:
    fields = {"subreddit": "synthetic_forum", "thread_title": "Synthetic thesis", "post_text": "Synthetic argument", "timestamp": "2026-07-04T00:00:00Z", "score": 30, "comment_count": 5}
    result = extract_reddit(response("thread", fields))
    assert result["document"]["items"][0]["subreddit"] == "synthetic_forum"
    assert result["document"]["verification_status"] == "auto_retrieved"
    assert extract_reddit(response("thread", fields, method="screenshot"))["requires_confirmation"] is True


def test_portfolio_and_broker_margin_extractors() -> None:
    portfolio_fields = {"cash": 1000, "total_equity": 5000, "margin_used": 0, "borrowed_amount": 0, "maintenance_margin_requirement": 0.25, "initial_margin_requirement": 0.5, "positions": [{"ticker": "SYNTH", "shares": 40, "average_cost": 80, "current_price": 100, "market_value": 4000, "unrealized_gain_loss": 800, "position_weight": 0.8, "user_intent": "hold"}]}
    portfolio = extract_portfolio_table(response("portfolio", portfolio_fields, method="screenshot"))
    assert portfolio["document"]["contract_version"] == "nhi.portfolio_snapshot.v1"
    assert portfolio["document"]["verification_status"] == "unverified_extraction"
    margin_fields = {"account_equity": 5000, "margin_used": 1000, "borrowed_amount": 1000, "maintenance_margin": 0.25, "initial_margin": 0.5, "margin_call_threshold": 3500, "buying_power": 2000, "cash": 500}
    margin = extract_broker_margin(response("margin", margin_fields, method="screenshot"))
    assert margin["document"]["borrowed_amount"] == 1000
    assert margin["requires_confirmation"] is True


def test_manual_note_and_confirmation_promotion() -> None:
    manual = extract_manual_note(response("note", {"text": "Real user-provided note"}, method="manual"))
    assert manual["document"]["verification_status"] == "user_verified"
    screenshot = extract_x_twitter(response("post", {"author_handle": "user", "post_text": "Captured text"}, method="screenshot"))
    confirmation = {
        "contract_version": "nhi.host_user_confirmation.v1", "confirmation_id": "confirm_1",
        "extraction_ref": {"extraction_id": screenshot["extraction"]["extraction_id"], "canonical_hash": screenshot["extraction"]["canonical_hash"]},
        "action": "correct", "corrections": {"post_text": "Corrected captured text"}, "confirmed_by_human": True,
    }
    confirmation["canonical_hash"] = contract_payload_hash(confirmation)
    promoted = apply_confirmation(screenshot, confirmation)
    assert promoted["extraction"]["verification_status"] == "user_corrected"
    assert promoted["document"]["verification_status"] == "user_corrected"
    assert promoted["document"]["items"][0]["post_text"] == "Corrected captured text"
