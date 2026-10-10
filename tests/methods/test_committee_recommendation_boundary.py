from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from capital_decision_lab.methods.runner import run_committee
from tests.orchestration.test_analyze_position import workflow_case

ROOT = Path(__file__).resolve().parents[2]


def test_committee_rejects_unknown_recommendation_and_never_falls_through() -> None:
    case = workflow_case()

    # Mock a method pack returning an unknown/hostile recommendation
    with patch("capital_decision_lab.methods.runner.run_method_pack") as mock_run:
        mock_run.return_value = {
            "contract_version": "nhi.method_pack_result.v1",
            "pack_id": "malicious_pack",
            "pack_name": "Malicious",
            "case_hash": "a" * 64,
            "data": {
                "model_implied_recommendation": {
                    "value": "hostile_arbitrary_verdict",
                    "provenance_class": "modeled",
                }
            },
            "required_user_authorization": True,
            "limitations": [],
        }

        # Must raise ValueError and NOT silently return recommendations[0] as synthesis
        with pytest.raises(ValueError, match="UNKNOWN_RECOMMENDATION_OUTPUT"):
            run_committee(["core"], case)


def test_committee_empty_packs_fails() -> None:
    with pytest.raises(ValueError, match="METHOD_PACKS_REQUIRED"):
        run_committee([], workflow_case())
