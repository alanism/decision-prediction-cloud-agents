"""Unranked side-by-side comparison orchestration."""

from __future__ import annotations

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash
from capital_decision_lab.contracts.validation import unavailable_result
from capital_decision_lab.orchestration.analyze import analyze_case


def compare_case(case: dict) -> dict:
    analyses = [
        analyze_case(case, alternative_id=item["alternative_id"])
        for item in case.get("alternatives", [])
    ]
    if len(analyses) < 2:
        raise ValueError("COMPARISON_REQUIRES_TWO_ALTERNATIVES")
    data: dict[str, dict] = {}
    for metric in analyses[0]["data"]:
        atoms = [analysis["data"][metric] for analysis in analyses]
        if all(atom["provenance_class"] == "unavailable" for atom in atoms):
            data[metric] = unavailable_result(
                "metric unavailable for every alternative",
                input_refs=[analysis["analysis_id"] for analysis in analyses],
            )
            continue
        provenance = "modeled" if any(atom["provenance_class"] == "modeled" for atom in atoms) else "calculated"
        data[metric] = {
            "value": {
                analysis["alternative_id"]: analysis["data"][metric]["value"]
                for analysis in analyses
            },
            "provenance_class": provenance,
            "input_refs": [analysis["analysis_id"] for analysis in analyses],
            "formula_ref": "comparison.side_by_side.v1",
            "limitations": ["Unranked comparison under the supplied assumptions"],
        }
    refs = [
        {"analysis_id": item["analysis_id"], "canonical_hash": item["canonical_hash"]}
        for item in analyses
    ]
    document = {
        "contract_version": "nhi.decision_comparison.v1",
        "comparison_id": f"comparison_{canonical_sha256(refs)[:16]}",
        "analysis_refs": refs,
        "data": data,
        "disclaimer": "comparison only, not financial advice",
        "report_sections": {
            "decision_summary": ["roi", "cagr", "volatility", "maximum_drawdown"],
            "kelly_sizing": ["full_kelly_fraction", "capped_exposure"],
            "convexity_upside_asymmetry": [
                "convexity_score", "upside_downside_multiple", "convexity_expected_value"
            ],
            "margin_safety": ["liquidation_buffer_percent", "current_margin_ratio"],
            "scenario_analysis": ["scenario_expected_return", "terminal_p50"],
            "unavailable_metrics": [
                name for name, atom in data.items() if atom["provenance_class"] == "unavailable"
            ],
            "warnings": ["kelly_warning", "margin_warning"],
            "provenance_and_hashes": {"analysis_hashes": [item["canonical_hash"] for item in analyses]},
        },
    }
    document["canonical_hash"] = contract_payload_hash(document)
    return {"comparison": document, "analyses": analyses}
