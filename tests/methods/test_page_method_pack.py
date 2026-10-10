from __future__ import annotations

from pathlib import Path

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.methods.packs import PACKS
from capital_decision_lab.methods.runner import (
    ALLOWED_COMMITTEE_RECOMMENDATIONS,
    available_method_packs,
    run_method_pack,
)
from tests.orchestration.test_analyze_position import workflow_case

ROOT = Path(__file__).resolve().parents[2]


def test_page_pack_registered_in_catalog() -> None:
    packs = available_method_packs()
    assert "page" in packs
    assert "page" in PACKS
    pack = PACKS["page"]
    assert pack["display_name"] == "Scott Page Many-Model"
    assert "claim_compiler" in pack["workflow_steps"]
    assert "power_law" in pack["calculation_modules"]


def test_page_pack_runs_on_workflow_case() -> None:
    case = workflow_case()
    result = run_method_pack("page", case)

    assert result["pack_id"] == "page"
    assert result["required_user_authorization"] is True
    assert result["contract_version"] == "nhi.method_pack_result.v1"
    assert result["data"]["model_implied_recommendation"]["provenance_class"] == "modeled"

    rec_type = result["data"]["model_implied_recommendation"]["value"]
    assert rec_type in ALLOWED_COMMITTEE_RECOMMENDATIONS

    issues = validate_contract(result)
    assert not issues, f"Contract validation failed: {issues}"


def test_page_pack_incorporates_heavy_tail_veto_if_present() -> None:
    case = workflow_case()
    # Add heavy tail observations with alpha ~ 1.8 <= 2.0
    obs = [10.0 * (1.0 + i * 0.2) for i in range(100)]
    case["model_thinking_inputs"] = {
        "power_law": {
            "observations": obs,
            "xmin": 10.0,
        }
    }
    result = run_method_pack("page", case)
    assert result["pack_id"] == "page"
    # Heavy-tail undefined mean should veto exposure increase
    rec_type = result["data"]["model_implied_recommendation"]["value"]
    assert rec_type != "increase exposure"
