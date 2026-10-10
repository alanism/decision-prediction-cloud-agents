"""Human-controlled assumption update proposals."""

from __future__ import annotations

import copy

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash


def create_assumption_proposal(update: dict) -> dict:
    data = update["data"]
    affected = data["affected_assumption"]["value"]
    proposal = {
        "contract_version": "nhi.assumption_update_proposal.v1",
        "proposal_id": f"assumption_proposal_{canonical_sha256(update)[:16]}",
        "prior_assumption": {"name": affected, "value": data["prior_probability"]["value"]},
        "proposed_assumption": {"name": affected, "value": data["posterior_probability"]["value"], "provenance_class": "forecast"},
        "evidence_refs": [update["synthesis_ref"]["canonical_hash"]],
        "evidence_batch_hash": update["synthesis_ref"]["canonical_hash"],
        "synthesis_hash": update["synthesis_ref"]["canonical_hash"],
        "sensitivity_map_hash": update["sensitivity_ref"]["canonical_hash"],
        "bayesian_update_hash": update["canonical_hash"],
        "affected_metric": affected or "unmapped",
        "affected_thesis_scenario": data["affected_scenario"]["value"],
        "projected_impacts": {"kelly": data["projected_impact_on_kelly"]["value"], "convexity": data["projected_impact_on_convexity"]["value"], "margin_safety": data["projected_impact_on_margin_safety"]["value"]},
        "approval_status": "pending",
    }
    proposal["canonical_hash"] = contract_payload_hash(proposal)
    return proposal


def apply_approved_proposal(case: dict, proposal: dict) -> dict:
    if proposal.get("approval_status") != "approved":
        return copy.deepcopy(case)
    proposed = proposal.get("proposed_assumption", {})
    name = proposed.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("PROPOSED_ASSUMPTION_NAME_REQUIRED")
    updated = copy.deepcopy(case)
    updated.setdefault("inputs", {})[name] = {
        "value": proposed.get("value"), "provenance_class": "forecast",
        "input_refs": [proposal["proposal_id"], proposal["bayesian_update_hash"]],
        "limitations": ["Applied only after explicit proposal approval."],
    }
    return updated
