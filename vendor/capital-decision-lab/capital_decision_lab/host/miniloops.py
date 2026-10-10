"""Actionable prompts for host extraction failures and missing inputs."""

from __future__ import annotations


PROMPTS = {
    "portfolio": ("MISSING_PORTFOLIO", "I need your current portfolio before I can produce a model-implied add, trim, or hold action. Upload a screenshot, paste a table, or import a CSV."),
    "broker_margin": ("MISSING_MARGIN", "Margin safety is blocked. Provide a broker margin screen or enter borrowing and maintenance requirements."),
    "polymarket": ("POLYMARKET_CONFIRMATION_REQUIRED", "Confirm or edit the extracted outcomes, probabilities, volume, and resolution date."),
    "x_twitter": ("X_TWITTER_CONFIRMATION_REQUIRED", "Confirm the extracted post text, author, timestamp, and engagement."),
    "reddit": ("REDDIT_CONFIRMATION_REQUIRED", "Confirm the extracted forum, thread or comment text, score, and relevance."),
    "manual_note": ("MANUAL_NOTE_REQUIRED", "Provide the note text and its relevance to the thesis."),
}


def prompt_for(source_type: str, *, reason: str | None = None) -> dict:
    code, prompt = PROMPTS.get(source_type, ("HOST_EXTRACTION_INPUT_REQUIRED", "Provide or confirm the required source fields."))
    result = {"code": code, "prompt": prompt}
    if reason:
        result["reason"] = reason
    return result
