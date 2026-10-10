from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "valid" / "guided-research"
NAMES = {
    "portfolio-basic-hold.json", "portfolio-margin-danger.json", "portfolio-concentrated-position.json", "portfolio-cash-available-add.json",
    "thesis-bullish-convex-stock.json", "thesis-bearish-margin-risk.json",
    "recommendation-increase-exposure.json", "recommendation-trim-to-kelly.json", "recommendation-hold-watch.json", "recommendation-avoid-margin.json", "recommendation-record-no-action.json",
    "source-polymarket-url-fed-decision.json", "source-polymarket-url-hormuz.json", "source-x-twitter-url-product-signal.json", "source-reddit-thread-retail-conviction.json",
    "connector-polymarket-api-success.json", "connector-polymarket-scrape-fallback.json", "connector-x-browser-extraction.json", "connector-reddit-public-json.json", "connector-source-unavailable.json",
}


def test_required_guided_research_fixtures_are_synthetic() -> None:
    paths = list(ROOT.glob("*.json"))
    assert {path.name for path in paths} == NAMES
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        serialized = json.dumps(value).casefold()
        assert "synthetic" in serialized
        assert "private_sentinel" not in serialized
