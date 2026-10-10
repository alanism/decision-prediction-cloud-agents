from __future__ import annotations

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.host.confirmation import apply_confirmation
from capital_decision_lab.host.extractors.x_twitter import extract_x_twitter
from capital_decision_lab.recommendation.engine import build_recommendation
from tests.host.test_source_extractors import response
from tests.recommendation.test_recommendation_engine import inputs


def screenshot_bundle() -> dict:
    return extract_x_twitter(response("post", {"author_handle": "synthetic", "post_text": "Real runtime captured text"}, method="screenshot"))


def confirmed_bundle() -> dict:
    bundle = screenshot_bundle()
    confirmation = {"contract_version": "nhi.host_user_confirmation.v1", "confirmation_id": "confirm_1", "extraction_ref": {"extraction_id": bundle["extraction"]["extraction_id"], "canonical_hash": bundle["extraction"]["canonical_hash"]}, "action": "confirm", "corrections": {}, "confirmed_by_human": True}
    confirmation["canonical_hash"] = contract_payload_hash(confirmation)
    return apply_confirmation(bundle, confirmation)


def test_unverified_host_screenshot_cannot_drive_recommendation() -> None:
    value = inputs(host_extractions=[screenshot_bundle()])
    result = build_recommendation(value)
    assert result["recommendation_type"] == "pause"
    assert "HOST_EVIDENCE_CONFIRMATION_REQUIRED" in result["reason_codes"]


def test_confirmed_host_evidence_can_drive_recommendation() -> None:
    result = build_recommendation(inputs(host_extractions=[confirmed_bundle()]))
    assert result["recommendation_type"] == "increase_exposure"
    assert result["evidence_reason"]["value"] == "host evidence is source-extracted and usable"


def test_contradictory_evidence_downgrades_to_watch() -> None:
    result = build_recommendation(inputs(host_extractions=[confirmed_bundle()], evidence_contradiction=0.8))
    assert result["recommendation_type"] == "watch"
    assert "EVIDENCE_CONTRADICTION" in result["reason_codes"]


def test_recommendation_exposes_separate_reason_atoms() -> None:
    result = build_recommendation(inputs(host_extractions=[confirmed_bundle()]))
    for name in ("kelly_reason", "convexity_reason", "margin_reason", "evidence_reason", "model_health_reason"):
        assert result[name]["provenance_class"] == "modeled"
