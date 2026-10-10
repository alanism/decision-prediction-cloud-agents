from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_proposal_and_authorization_are_separate_hash_bound_contracts() -> None:
    proposal_path = ROOT / "schemas" / "decision-proposal.v1.schema.json"
    authorization_path = ROOT / "schemas" / "decision-authorization.v1.schema.json"
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))

    assert proposal_path != authorization_path
    assert proposal["properties"]["contract_version"]["const"] == "nhi.decision_proposal.v1"
    assert "authorization" not in proposal["properties"]
    assert authorization["properties"]["contract_version"]["const"] == "nhi.decision_authorization.v1"
    assert {"proposal_ref", "analysis_ref", "confirmed_by_human"} <= set(authorization["required"])
    proposal_ref = authorization["$defs"]["proposal_reference"]
    analysis_ref = authorization["$defs"]["analysis_reference"]
    assert {"proposal_id", "canonical_hash"} <= set(proposal_ref["required"])
    assert {"analysis_id", "canonical_hash"} <= set(analysis_ref["required"])


def test_deferred_outcome_schema_is_not_created() -> None:
    assert not (ROOT / "schemas" / "decision-outcome.v1.schema.json").exists()


def test_no_proposal_or_authorization_creation_behavior_exists() -> None:
    from capital_decision_lab.contracts import authorization

    assert not hasattr(authorization, "create_proposal")
    assert not hasattr(authorization, "create_authorization")
