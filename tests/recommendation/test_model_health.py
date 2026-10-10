from __future__ import annotations

from capital_decision_lab.recommendation.health import evaluate_model_health


def test_model_health_states_and_reason_codes() -> None:
    healthy = evaluate_model_health(contradiction=0.1, edge_compression=0.1, drawdown_ratio=0.4, margin_stress=0.1, kill_condition_triggered=False, confidence=0.9, staleness=0.1)
    assert healthy["state"] == "healthy"
    degrading = evaluate_model_health(contradiction=0.8, edge_compression=0.8, drawdown_ratio=1.5, margin_stress=0.7, kill_condition_triggered=False, confidence=0.3, staleness=0.8)
    assert degrading["state"] == "degrading"
    assert {"EVIDENCE_CONTRADICTION", "EDGE_COMPRESSION", "MARGIN_STRESS"} <= set(degrading["reason_codes"])
    broken = evaluate_model_health(contradiction=0.2, edge_compression=0.2, drawdown_ratio=1.0, margin_stress=0.2, kill_condition_triggered=True, confidence=0.8, staleness=0.1)
    assert broken["state"] == "broken"


def test_model_health_outputs_are_provenance_labeled() -> None:
    result = evaluate_model_health(contradiction=0.4, edge_compression=0.3, drawdown_ratio=0.8, margin_stress=0.2, kill_condition_triggered=False, confidence=0.7, staleness=0.2)
    assert result["data"]["confidence"]["provenance_class"] == "modeled"
    assert result["data"]["impact_on_kelly"]["provenance_class"] == "forecast"
    assert len(result["canonical_hash"]) == 64
