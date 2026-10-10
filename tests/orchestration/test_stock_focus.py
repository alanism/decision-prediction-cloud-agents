from __future__ import annotations

import copy
import json
from pathlib import Path

from capital_decision_lab.contracts.validation import validate_contract, validate_evidence_atom
from capital_decision_lab.orchestration.analyze import analyze_case
from capital_decision_lab.orchestration.compare import compare_case


ROOT = Path(__file__).resolve().parents[2]


def _focused_case() -> dict:
    case = json.loads((ROOT / "fixtures" / "valid" / "mvp-case.json").read_text(encoding="utf-8"))
    stock_root = ROOT / "fixtures" / "valid" / "stock-exposure"
    case["focus"] = "stock_exposure"
    case["inputs"]["kelly_stock"] = {
        "value": json.loads((stock_root / "kelly-stock-thesis.json").read_text(encoding="utf-8"))["inputs"],
        "provenance_class": "assumed"
    }
    case["inputs"]["convexity_scenarios"] = {
        "value": json.loads((stock_root / "convex-upside-stock.json").read_text(encoding="utf-8"))["inputs"],
        "provenance_class": "assumed"
    }
    case["inputs"]["margin_inputs"] = {
        "value": json.loads((stock_root / "margin-danger.json").read_text(encoding="utf-8"))["inputs"],
        "provenance_class": "assumed"
    }
    return case


def test_stock_focused_analysis_adds_pillars_without_losing_existing_metrics() -> None:
    result = analyze_case(_focused_case(), alternative_id="alt_a")
    legacy = {"roi", "cagr", "volatility", "maximum_drawdown", "sharpe", "sortino", "calmar"}
    pillars = {
        "full_kelly_fraction", "confidence_adjusted_kelly", "capped_exposure",
        "convexity_score", "upside_downside_multiple", "breakeven_probability",
        "current_margin_ratio", "estimated_margin_call_price", "liquidation_buffer_percent",
        "margin_stress_table", "margin_warning",
    }
    assert legacy <= set(result["data"])
    assert pillars <= set(result["data"])
    assert all(validate_evidence_atom(result["data"][name]) == [] for name in pillars)
    assert validate_contract(result) == []


def test_analysis_report_has_eight_stock_priority_sections() -> None:
    result = analyze_case(_focused_case(), alternative_id="alt_a")
    assert list(result["report_sections"]) == [
        "decision_summary",
        "kelly_sizing",
        "convexity_upside_asymmetry",
        "margin_safety",
        "scenario_analysis",
        "unavailable_metrics",
        "warnings",
        "provenance_and_hashes",
    ]
    assert "roi" in result["report_sections"]["decision_summary"]
    assert "full_kelly_fraction" in result["report_sections"]["kelly_sizing"]


def test_stock_focused_comparison_remains_unranked() -> None:
    case = _focused_case()
    result = compare_case(case)
    comparison = result["comparison"]
    for name in (
        "full_kelly_fraction",
        "capped_exposure",
        "convexity_score",
        "upside_downside_multiple",
        "liquidation_buffer_percent",
    ):
        assert name in comparison["data"]
    assert "ranking" not in comparison
    assert "selected_alternative" not in comparison
