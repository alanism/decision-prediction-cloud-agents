from __future__ import annotations

from pathlib import Path

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.methods.runner import run_committee
from tests.orchestration.test_analyze_position import workflow_case

ROOT = Path(__file__).resolve().parents[2]


def test_committee_runs_with_page_and_core() -> None:
    case = workflow_case()
    result = run_committee(["core", "page"], case)

    assert result["contract_version"] == "nhi.committee_result.v1"
    assert result["required_user_authorization"] is True
    assert len(result["pack_results"]) == 2
    assert result["data"]["binding_constraint"]["provenance_class"] == "modeled"

    issues = validate_contract(result)
    assert not issues, f"Contract validation failed: {issues}"


def test_committee_applies_heavy_tail_veto_as_binding_constraint() -> None:
    case = workflow_case()
    # Add heavy tail observations with alpha ~ 1.8 <= 2.0
    obs = [10.0 * (1.0 + i * 0.2) for i in range(100)]
    case["model_thinking_inputs"] = {
        "input_trust_class": "user_verified",
        "power_law": {
            "input_trust_class": "user_verified",
            "observations": obs,
            "xmin": 10.0,
        },
    }
    result = run_committee(["core", "page"], case)
    assert result["contract_version"] == "nhi.committee_result.v1"
    # Page emits "watch" due to heavy tail undefined mean, which overrides core "increase exposure"
    assert result["data"]["hermes_synthesis"]["value"] in {"watch", "hold current exposure"}
    assert result["data"]["binding_constraint"]["value"] == "page"
