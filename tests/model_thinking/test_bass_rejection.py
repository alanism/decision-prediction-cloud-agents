from __future__ import annotations

from pathlib import Path

from capital_decision_lab.calculations.bass import analyze_bass_input, simulate_bass_diffusion
from capital_decision_lab.contracts.canonical import contract_payload_hash

ROOT = Path(__file__).resolve().parents[2]


def test_bass_rejects_negative_parameters() -> None:
    res_p = simulate_bass_diffusion(10000.0, -0.01, 0.30)
    assert res_p["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "innovation and imitation rates must be non-negative" in res_p["data"]["cumulative_adopters"]["reason"]

    res_q = simulate_bass_diffusion(10000.0, 0.03, -0.10)
    assert res_q["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "innovation and imitation rates must be non-negative" in res_q["data"]["cumulative_adopters"]["reason"]


def test_bass_rejects_sum_exceeding_one() -> None:
    res = simulate_bass_diffusion(10000.0, 0.60, 0.50)
    assert res["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "sum of innovation and imitation rates must not exceed 1.0" in res["data"]["cumulative_adopters"]["reason"]


def test_bass_rejects_zero_innovation_with_zero_initial_adopters() -> None:
    # Stagnant diffusion: p=0 and N0=0 means delta N is always 0
    res = simulate_bass_diffusion(10000.0, 0.0, 0.40, initial_adopters=0.0)
    assert res["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "positive adoption requires either positive innovation rate or non-zero initial adopters" in res["data"]["cumulative_adopters"]["reason"]


def test_bass_rejects_nonfinite_or_boolean_parameters() -> None:
    res_nan = simulate_bass_diffusion(float("nan"), 0.03, 0.38)
    assert res_nan["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "parameters must be finite numbers" in res_nan["data"]["cumulative_adopters"]["reason"]

    res_bool = simulate_bass_diffusion(10000.0, True, 0.38)  # type: ignore
    assert res_bool["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "parameters must be finite numbers" in res_bool["data"]["cumulative_adopters"]["reason"]


def test_bass_rejects_market_potential_bounds() -> None:
    res_zero = simulate_bass_diffusion(0.0, 0.03, 0.38)
    assert res_zero["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "market potential must be positive and at most 1e9" in res_zero["data"]["cumulative_adopters"]["reason"]

    res_huge = simulate_bass_diffusion(2e9, 0.03, 0.38)
    assert res_huge["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "market potential must be positive and at most 1e9" in res_huge["data"]["cumulative_adopters"]["reason"]


def test_bass_rejects_initial_adopter_bounds() -> None:
    res_neg = simulate_bass_diffusion(10000.0, 0.03, 0.38, initial_adopters=-50.0)
    assert res_neg["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "initial adopters must be between 0 and market potential" in res_neg["data"]["cumulative_adopters"]["reason"]

    res_over = simulate_bass_diffusion(10000.0, 0.03, 0.38, initial_adopters=15000.0)
    assert res_over["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "initial adopters must be between 0 and market potential" in res_over["data"]["cumulative_adopters"]["reason"]


def test_bass_rejects_horizon_bounds() -> None:
    res_zero = simulate_bass_diffusion(10000.0, 0.03, 0.38, horizon=0)
    assert res_zero["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "horizon must be between 1 and 10000 periods" in res_zero["data"]["cumulative_adopters"]["reason"]

    res_huge = simulate_bass_diffusion(10000.0, 0.03, 0.38, horizon=20000)
    assert res_huge["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "horizon must be between 1 and 10000 periods" in res_huge["data"]["cumulative_adopters"]["reason"]


def test_bass_rejects_untrusted_input_envelope() -> None:
    model_input = {
        "contract_version": "nhi.model_input.v1",
        "model_id": "bass_diffusion",
        "model_family": "bass",
        "model_version": "1.0.0",
        "input_trust_class": "untrusted_external",
        "parameters": {
            "market_potential": 10000.0,
            "innovation_rate": 0.03,
            "imitation_rate": 0.38,
            "initial_adopters": 0.0,
            "horizon": 10,
        },
    }
    model_input["canonical_hash"] = contract_payload_hash(model_input)
    res = analyze_bass_input(model_input)
    assert res["data"]["cumulative_adopters"]["provenance_class"] == "unavailable"
    assert "untrusted input requires user confirmation" in res["data"]["cumulative_adopters"]["reason"]
