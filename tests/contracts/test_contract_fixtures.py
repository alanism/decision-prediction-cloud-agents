from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.contracts import validation


ROOT = Path(__file__).resolve().parents[2]
VALID_ROOT = ROOT / "fixtures" / "valid" / "contracts"
ADVERSARIAL_ROOT = ROOT / "fixtures" / "adversarial" / "contracts"


def test_schema_loader_resolves_all_contract_versions() -> None:
    versions = validation.supported_contract_versions()
    assert versions == (
        "nhi.assumption_register.v1",
        "nhi.assumption_update_proposal.v1",
        "nhi.bayesian_update.v1",
        "nhi.belief_state.v1",
        "nhi.committee_result.v1",
        "nhi.decision_analysis.v1",
        "nhi.decision_authorization.v1",
        "nhi.decision_case.v1",
        "nhi.decision_comparison.v1",
        "nhi.decision_ledger.v1",
        "nhi.decision_proposal.v1",
        "nhi.ensemble_result.v1",
        "nhi.event_market_signal.v1",
        "nhi.event_market_snapshot.v1",
        "nhi.evidence_batch.v1",
        "nhi.evidence_item.v1",
        "nhi.evidence_source.v1",
        "nhi.host_capability_request.v1",
        "nhi.host_capability_response.v1",
        "nhi.host_extraction_result.v1",
        "nhi.host_source_artifact.v1",
        "nhi.host_user_confirmation.v1",
        "nhi.kill_condition.v1",
        "nhi.method_pack.v1",
        "nhi.method_pack_result.v1",
        "nhi.method_pack_run.v1",
        "nhi.model_input.v1",
        "nhi.model_result.v1",
        "nhi.portfolio_intent.v1",
        "nhi.portfolio_position.v1",
        "nhi.portfolio_snapshot.v1",
        "nhi.recommendation.v1",
        "nhi.recommendation_authorization.v1",
        "nhi.scenario_assumption.v1",
        "nhi.social_evidence_signal.v1",
        "nhi.stock_thesis.v1",
        "nhi.thesis_sensitivity_map.v1",
    )
    for version in versions:
        schema = validation.load_schema(version)
        assert schema["properties"]["contract_version"]["const"] == version


def test_all_valid_contract_fixtures_pass() -> None:
    fixtures = sorted(VALID_ROOT.glob("*.json"))
    assert len(fixtures) == 7
    for path in fixtures:
        document = json.loads(path.read_text(encoding="utf-8"))
        assert validation.validate_contract(document) == [], path.name


def test_all_adversarial_contract_fixtures_fail_with_expected_code() -> None:
    fixtures = sorted(ADVERSARIAL_ROOT.glob("*.json"))
    assert len(fixtures) >= 5
    for path in fixtures:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        issues = validation.validate_contract(fixture["document"])
        assert fixture["expected_issue_code"] in {item["code"] for item in issues}, path.name
