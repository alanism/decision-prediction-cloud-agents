from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.evidence.event_market import analyze_event_market
from capital_decision_lab.evidence.social import analyze_social


ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "valid" / "evidence"

EVENT_NAMES = {
    "fed-strong-no-change-consensus.json", "fed-split-decision-high-volatility.json",
    "fed-cut-consensus-liquidity-tailwind.json", "fed-cut-consensus-recession-signal.json",
    "geopolitics-hormuz-disruption-oil-shock.json", "geopolitics-hormuz-normalization-risk-off-relief.json",
    "technology-ai-model-leadership-anthropic.json", "technology-ai-release-timing.json",
    "market-structure-largest-company-nvidia.json", "commodities-wti-threshold.json",
    "commodities-gold-risk-off.json", "low-volume-weak-signal.json",
    "unverified-screenshot-extraction-blocked.json", "same-event-bullish-for-oil-bearish-for-airline.json",
    "same-fed-cut-bullish-liquidity-bearish-recession.json",
}
X_NAMES = {
    "x-twitter-bullish-narrative-momentum.json", "x-twitter-bearish-regulatory-shock.json",
    "x-twitter-duplicate-claims-crowding-risk.json", "x-twitter-low-credibility-noise.json",
    "x-twitter-high-credibility-product-signal.json", "x-twitter-unverified-extraction-blocked.json",
}
REDDIT_NAMES = {
    "reddit-retail-conviction-bullish.json", "reddit-bearish-counterarguments.json",
    "reddit-echo-chamber-risk.json", "reddit-disagreement-high-volatility.json",
    "reddit-duplicate-claims.json", "reddit-unverified-extraction-blocked.json",
}
COMBINED_NAMES = {
    "combined-polymarket-x-reddit-bullish-aligned.json",
    "combined-polymarket-bullish-social-bearish-contradiction.json",
    "combined-high-volatility-mixed-evidence.json",
    "combined-low-quality-evidence-blocked-or-discounted.json",
    "combined-approved-update-affects-kelly-convexity-margin.json",
    "combined-pending-update-does-not-affect-analysis.json",
}


def test_all_33_required_synthetic_fixtures_exist_and_run() -> None:
    assert {path.name for path in (ROOT / "event-market").glob("*.json")} == EVENT_NAMES
    assert {path.name for path in (ROOT / "x-twitter").glob("*.json")} == X_NAMES
    assert {path.name for path in (ROOT / "reddit").glob("*.json")} == REDDIT_NAMES
    assert {path.name for path in (ROOT / "combined").glob("*.json")} == COMBINED_NAMES
    for path in (ROOT / "event-market").glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        assert validate_contract(value) == [], path.name
        assert analyze_event_market(value)["data"]
    for folder in ("x-twitter", "reddit"):
        for path in (ROOT / folder).glob("*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            assert validate_contract(value) == [], path.name
            assert analyze_social(value)["data"]
    for path in (ROOT / "combined").glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        assert value["fixture_class"] == "synthetic"
        assert value["signals"]
