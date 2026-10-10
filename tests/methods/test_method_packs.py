from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.methods.runner import available_method_packs, run_committee, run_method_pack
from capital_decision_lab.plugin.commands import run_cli
from tests.orchestration.test_analyze_position import response, social_fields, workflow_case, write_inputs


def test_first_party_method_list_and_core_run() -> None:
    assert available_method_packs() == ["committee", "contrarian_filings", "core", "mauboussin", "page", "thorp"]
    result = run_method_pack("core", workflow_case())
    assert result["pack_id"] == "core"
    assert result["required_user_authorization"] is True
    assert result["data"]["model_implied_recommendation"]["provenance_class"] == "modeled"


def test_method_pack_schemas_declare_exact_contracts() -> None:
    root = Path(__file__).resolve().parents[2] / "schemas"
    expected = {"method-pack.v1.schema.json": "nhi.method_pack.v1", "method-pack-run.v1.schema.json": "nhi.method_pack_run.v1", "method-pack-result.v1.schema.json": "nhi.method_pack_result.v1", "committee-result.v1.schema.json": "nhi.committee_result.v1"}
    for filename, version in expected.items():
        schema = json.loads((root / filename).read_text(encoding="utf-8"))
        assert schema["properties"]["contract_version"]["const"] == version
        assert schema["required"]


def test_thorp_fractional_kelly_and_margin_override() -> None:
    result = run_method_pack("thorp", workflow_case())
    assert result["data"]["target_exposure"]["value"] <= result["data"]["full_kelly"]["value"] / 2
    danger = workflow_case(); danger["decision_case"]["inputs"]["margin_inputs"]["value"].update({"borrowed_amount": 7000, "position_market_value": 10000, "maintenance_margin_requirement": 0.35, "shares": 100})
    assert run_method_pack("thorp", danger)["data"]["model_implied_recommendation"]["value"] == "avoid margin"


def test_mauboussin_requires_probabilities_and_flags_base_rate_gap() -> None:
    missing = workflow_case(); missing["thesis"]["probabilities"] = None
    assert "NUMERICAL_PROBABILITIES_REQUIRED" in run_method_pack("mauboussin", missing)["data"]["red_flags"]["value"]
    case = workflow_case(); case["method_inputs"] = {"base_rate": 0.2}
    assert "BASE_RATE_OVERCONFIDENCE" in run_method_pack("mauboussin", case)["data"]["red_flags"]["value"]


def test_contrarian_requires_and_uses_primary_filing_evidence() -> None:
    missing = run_method_pack("contrarian_filings", workflow_case())
    assert "PRIMARY_FILINGS_REQUIRED" in missing["data"]["red_flags"]["value"]
    case = workflow_case(); case["filing_evidence"] = [{"source_type": "filings", "verification_status": "auto_retrieved", "artifact_hash": "a" * 64}]
    used = run_method_pack("contrarian_filings", case)
    assert used["data"]["evidence_used"]["value"] == ["filings"]


def test_committee_detects_agreement_disagreement_and_synthesizes() -> None:
    agreement = run_committee(["core", "core"], workflow_case())
    assert agreement["data"]["agreement"]["value"] is True
    disagreement = run_committee(["core", "contrarian_filings", "thorp"], workflow_case())
    assert disagreement["data"]["agreement"]["value"] is False
    assert disagreement["data"]["hermes_synthesis"]["value"]
    assert disagreement["required_user_authorization"] is True


def test_method_cli_and_analyze_position_flag(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir(); case_path = local / "case.json"
    case_path.write_text(json.dumps(workflow_case()), encoding="utf-8")
    code, listed = run_cli(["method", "list"], local_root=local)
    assert code == 0 and "thorp" in listed["method_packs"]
    code, run = run_cli(["method", "run", "--pack", "thorp", "--case", str(case_path)], local_root=local)
    assert code == 0 and run["method_result"]["pack_id"] == "thorp"
    code, committee = run_cli(["method", "committee", "--packs", "core", "thorp", "--case", str(case_path)], local_root=local)
    assert code == 0 and len(committee["committee_result"]["pack_results"]) == 2
    folder = local / "host"; write_inputs(folder, [response("x_twitter", social_fields())])
    code, analyzed = run_cli(["analyze-position", "--case", str(case_path), "--host-inputs", str(folder), "--method", "thorp"], local_root=local)
    assert code == 0 and analyzed["method_result"]["pack_id"] == "thorp"


def test_unknown_method_fails_clearly(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir(); case_path = local / "case.json"
    case_path.write_text(json.dumps(workflow_case()), encoding="utf-8")
    code, result = run_cli(["method", "run", "--pack", "unknown", "--case", str(case_path)], local_root=local)
    assert code == 2 and result["issues"] == [{"code": "METHOD_PACK_UNKNOWN"}]
    folder = local / "host"; write_inputs(folder, [response("x_twitter", social_fields())])
    code, result = run_cli(["analyze-position", "--case", str(case_path), "--host-inputs", str(folder), "--method", "unknown"], local_root=local)
    assert code == 2 and result["issues"] == [{"code": "METHOD_PACK_UNKNOWN"}]
