from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.calculations import allocation, convexity, margin


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "valid" / "stock-exposure"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_required_stock_fixtures_are_synthetic_and_executable() -> None:
    names = {
        "kelly-stock-thesis.json",
        "negative-edge-kelly.json",
        "convex-upside-stock.json",
        "margin-stress.json",
        "margin-danger.json",
    }
    assert {path.name for path in FIXTURES.glob("*.json")} == names
    for name in names:
        fixture = _load(name)
        assert fixture["fixture_class"] == "valid_synthetic_stock_exposure"
        if fixture["engine"] == "kelly":
            result = allocation.analyze_kelly(fixture["inputs"])
        elif fixture["engine"] == "convexity":
            result = convexity.analyze_convexity(fixture["inputs"])
        else:
            result = margin.analyze_margin(fixture["inputs"])
        assert result


def test_negative_edge_and_margin_danger_emit_warnings_without_actions() -> None:
    negative = allocation.analyze_kelly(_load("negative-edge-kelly.json")["inputs"])
    danger = margin.analyze_margin(_load("margin-danger.json")["inputs"])
    assert negative["capped_exposure"]["value"] == 0.0
    assert "negative edge" in negative["kelly_warning"]["value"]
    assert "threshold" in danger["margin_warning"]["value"]
    combined = str({"negative": negative, "danger": danger}).lower()
    assert "you should" not in combined
    assert "recommended" not in combined

