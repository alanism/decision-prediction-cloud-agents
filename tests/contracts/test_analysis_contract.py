from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_analysis_contract_declares_all_provenance_classes() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "decision-analysis.v1.schema.json").read_text(encoding="utf-8")
    )
    classes = schema["$defs"]["evidence_atom"]["properties"]["provenance_class"]["enum"]
    assert classes == [
        "measured",
        "assumed",
        "calculated",
        "modeled",
        "forecast",
        "decided",
        "unavailable",
    ]


def test_every_decision_content_schema_requires_evidence_atoms() -> None:
    for name in ("decision-analysis.v1.schema.json", "decision-comparison.v1.schema.json"):
        schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        atom = schema["$defs"]["evidence_atom"]
        assert schema["properties"]["data"]["additionalProperties"] == {
            "$ref": "#/$defs/evidence_atom"
        }
        assert {"value", "provenance_class"} <= set(atom["required"])
        assert atom["additionalProperties"] is False
        assert {
            "unit",
            "input_refs",
            "formula_ref",
            "limitations",
            "reason",
        } <= set(atom["properties"])

    proposal = json.loads(
        (ROOT / "schemas" / "decision-proposal.v1.schema.json").read_text(encoding="utf-8")
    )
    selected = proposal["properties"]["selected_action"]
    assert {"value", "provenance_class"} <= set(selected["required"])
    assert selected["properties"]["provenance_class"]["const"] == "decided"
