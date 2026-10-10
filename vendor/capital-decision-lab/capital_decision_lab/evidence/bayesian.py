"""Bounded odds-form belief updates linked to explicit thesis rules."""

from __future__ import annotations

import math

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash

from .common import atom, atom_value, clamp
from .sensitivity import match_sensitivity


def bayesian_probability(prior_probability: float, likelihood_ratio: float, *, likelihood_bounds: tuple[float, float] = (0.5, 2.0), maximum_update: float = 0.10) -> float:
    prior = float(prior_probability)
    if not 0 < prior < 1:
        raise ValueError("PRIOR_PROBABILITY_INVALID")
    ratio = max(likelihood_bounds[0], min(likelihood_bounds[1], float(likelihood_ratio)))
    odds = prior / (1.0 - prior)
    posterior = odds * ratio / (1.0 + odds * ratio)
    posterior = max(prior - maximum_update, min(prior + maximum_update, posterior))
    return max(1e-12, min(1.0 - 1e-12, posterior))


def build_belief_update(belief: dict, synthesis: dict, sensitivity_map: dict, *, maximum_update: float = 0.10) -> dict:
    prior = float(belief["prior_probability"])
    match = match_sensitivity(synthesis, sensitivity_map)
    bull = clamp(atom_value(synthesis, "bullish_pressure"))
    bear = clamp(atom_value(synthesis, "bearish_pressure"))
    evidence_weight = clamp(atom_value(synthesis, "evidence_weight")) * match["weight_multiplier"]
    direction = match["direction_for_thesis"]
    pressure = bull - bear
    if pressure == 0.0:
        pressure = clamp(atom_value(synthesis, "event_evidence_strength", 0.0))
    if direction == "bearish":
        pressure *= -1.0
    elif direction not in {"bullish", "bearish"}:
        pressure = 0.0
    ratio = max(0.5, min(2.0, math.exp(pressure * evidence_weight)))
    posterior = bayesian_probability(prior, ratio, maximum_update=maximum_update) if match["matched"] else prior
    update_direction = "increase" if posterior > prior else "decrease" if posterior < prior else "unchanged"
    limitations = ["Bounded model inference under verified evidence and an explicit thesis sensitivity rule."]
    data = {
        "prior_probability": atom(prior, "calculated", unit="probability", input_refs=[belief["belief_id"]]),
        "likelihood_ratio": atom(ratio, "modeled", unit="ratio", formula_ref="bounded_odds_likelihood_ratio"),
        "posterior_probability": atom(posterior, "forecast", unit="probability", input_refs=[belief["belief_id"], synthesis["canonical_hash"], sensitivity_map["canonical_hash"]], limitations=limitations),
        "update_direction": atom(update_direction, "modeled"),
        "evidence_weight": atom(evidence_weight, "modeled", unit="score"),
        "confidence": atom(clamp(atom_value(synthesis, "confidence") * match["weight_multiplier"]), "modeled", unit="score"),
        "affected_assumption": atom(match["affected_assumption"], "modeled"),
        "affected_scenario": atom("thesis_mapped", "modeled"),
        "maximum_update_cap": atom(maximum_update, "calculated", unit="probability"),
        "projected_impact_on_kelly": atom("recalculate win probability after approval", "forecast", limitations=limitations),
        "projected_impact_on_convexity": atom("recalculate mapped scenario after approval", "forecast", limitations=limitations),
        "projected_impact_on_margin_safety": atom("recalculate mapped stress assumption after approval", "forecast", limitations=limitations),
    }
    document = {
        "contract_version": "nhi.bayesian_update.v1",
        "update_id": f"belief_update_{canonical_sha256([belief['belief_id'], synthesis['canonical_hash'], sensitivity_map['canonical_hash']])[:16]}",
        "belief_ref": {"id": belief["belief_id"], "canonical_hash": belief["canonical_hash"]},
        "synthesis_ref": {"canonical_hash": synthesis["canonical_hash"]},
        "sensitivity_ref": {"id": sensitivity_map["map_id"], "canonical_hash": sensitivity_map["canonical_hash"]},
        "data": data,
    }
    document["canonical_hash"] = contract_payload_hash(document)
    return document
