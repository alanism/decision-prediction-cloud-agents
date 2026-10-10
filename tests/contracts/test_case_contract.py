from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_NAMES = (
    "decision-case.v1.schema.json",
    "assumption-register.v1.schema.json",
    "decision-analysis.v1.schema.json",
    "decision-comparison.v1.schema.json",
    "decision-proposal.v1.schema.json",
    "decision-authorization.v1.schema.json",
    "decision-ledger.v1.schema.json",
)


def test_case_and_assumption_schemas_are_distinct_valid_json() -> None:
    case = json.loads((ROOT / "schemas" / "decision-case.v1.schema.json").read_text(encoding="utf-8"))
    assumptions = json.loads(
        (ROOT / "schemas" / "assumption-register.v1.schema.json").read_text(encoding="utf-8")
    )
    assert case["properties"]["contract_version"]["const"] == "nhi.decision_case.v1"
    assert assumptions["properties"]["contract_version"]["const"] == "nhi.assumption_register.v1"


def test_every_contract_declares_schema_and_version_identity() -> None:
    for name in SCHEMA_NAMES:
        schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].endswith(name)
        version = schema["properties"]["contract_version"]["const"]
        assert version.startswith("nhi.") and version.endswith(".v1")
