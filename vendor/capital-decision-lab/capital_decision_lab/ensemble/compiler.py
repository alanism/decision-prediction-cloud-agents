"""Deterministic claim compiler and ensemble aggregation."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from capital_decision_lab.contracts.canonical import contract_payload_hash

HEX_64_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
VALID_DIRECTIONS = {"positive", "negative", "neutral"}
MAX_CLAIM_ID_LENGTH = 256
THRESHOLD_CONSTANT_VERSION = "page_supermajority_v1"


def compile_claim_ensemble(
    claims: list[dict[str, Any]],
    *,
    binding_vetoes: list[str] | None = None,
    correlation_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compile and aggregate claims into an nhi.ensemble_result.v1 contract envelope."""
    if not isinstance(claims, list) or len(claims) == 0:
        raise ValueError("claims list cannot be empty")

    contributing_receipt_hashes: set[str] = set()
    all_families: set[str] = set()
    claims_by_id: dict[str, list[dict[str, Any]]] = {}
    correlated_groups: set[str] = set()

    for c in claims:
        if not isinstance(c, dict):
            raise ValueError("each claim must be a dictionary record")

        for req in ("claim_id", "model_family", "direction", "receipt_hash"):
            if req not in c or c[req] is None:
                raise ValueError("claim record missing required fields")

        claim_id = str(c["claim_id"]).strip()
        if len(claim_id) == 0 or len(claim_id) > MAX_CLAIM_ID_LENGTH:
            raise ValueError("claim identifier exceeds maximum length")

        direction = str(c["direction"]).lower().strip()
        if direction not in VALID_DIRECTIONS:
            raise ValueError(f"invalid claim direction: {direction}")

        receipt_hash = str(c["receipt_hash"]).strip()
        if not HEX_64_PATTERN.match(receipt_hash):
            raise ValueError("receipt_hash must be a 64-character hex string")

        contributing_receipt_hashes.add(receipt_hash.lower())
        family = str(c["model_family"]).strip()
        all_families.add(family)

        corr_group = c.get("correlation_group")
        if corr_group:
            correlated_groups.add(str(corr_group))

        if claim_id not in claims_by_id:
            claims_by_id[claim_id] = []
        claims_by_id[claim_id].append(c)

    robust_positive: list[str] = []
    conditional: list[str] = []
    disputed: list[str] = []
    vetoes = list(binding_vetoes or [])

    for claim_id, claim_records in claims_by_id.items():
        # Determine families contributing to this claim
        families = {c["model_family"] for c in claim_records}
        num_families = len(families)

        # Collapse votes by correlation group / independent family
        group_votes: dict[str, list[str]] = {}
        for c in claim_records:
            group_key = c.get("correlation_group") or c["model_family"]
            if group_key not in group_votes:
                group_votes[group_key] = []
            group_votes[group_key].append(c["direction"])

        # Determine effective direction per group
        pos_groups = 0
        neg_groups = 0
        for grp_key, directions in group_votes.items():
            if all(d == "positive" for d in directions):
                pos_groups += 1
            elif any(d == "negative" for d in directions):
                neg_groups += 1
            elif any(d == "positive" for d in directions):
                pos_groups += 1

        total_groups = len(group_votes)
        supermajority_threshold = max(2, math.ceil(2.0 * float(total_groups) / 3.0))

        if len(vetoes) > 0:
            # Binding vetoes suppress robust_positive
            if pos_groups > 0:
                conditional.append(claim_id)
            else:
                disputed.append(claim_id)
        elif num_families >= 2 and pos_groups >= supermajority_threshold:
            robust_positive.append(claim_id)
        elif pos_groups > 0 and num_families < 2:
            # Only 1 family supporting -> conditional
            conditional.append(claim_id)
        elif pos_groups > 0 and neg_groups == 0:
            conditional.append(claim_id)
        else:
            disputed.append(claim_id)

    hasher = hashlib.sha256()
    for h in sorted(contributing_receipt_hashes):
        hasher.update(h.encode("utf-8"))
    for rp in sorted(robust_positive):
        hasher.update(rp.encode("utf-8"))
    ensemble_id = f"ensemble_{hasher.hexdigest()[:16]}"

    doc: dict[str, Any] = {
        "contract_version": "nhi.ensemble_result.v1",
        "ensemble_id": ensemble_id,
        "aggregated_by": "engine",
        "contributing_receipt_hashes": sorted(contributing_receipt_hashes),
        "applicable_family_count": len(all_families),
        "threshold_constant_version": THRESHOLD_CONSTANT_VERSION,
        "correlated_models": sorted(correlated_groups),
        "claims": {
            "robust_positive": sorted(robust_positive),
            "conditional": sorted(conditional),
            "disputed": sorted(disputed),
        },
        "binding_vetoes": sorted(vetoes),
        "limitations": [
            f"Ensemble claims aggregated deterministically under {THRESHOLD_CONSTANT_VERSION} rules."
        ],
    }
    doc["canonical_hash"] = contract_payload_hash(doc)
    return doc
