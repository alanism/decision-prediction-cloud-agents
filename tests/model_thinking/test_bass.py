from __future__ import annotations

import math
from pathlib import Path

from capital_decision_lab.calculations.bass import simulate_bass_diffusion
from capital_decision_lab.contracts.validation import validate_contract

ROOT = Path(__file__).resolve().parents[2]


def test_bass_oracle_step_progression() -> None:
    # M = 10,000, p = 0.03, q = 0.38, N0 = 0, horizon = 10
    M = 10000.0
    p = 0.03
    q = 0.38
    horizon = 10

    res = simulate_bass_diffusion(M, p, q, initial_adopters=0.0, horizon=horizon)

    assert res["contract_version"] == "nhi.model_result.v1"
    assert res["model_family"] == "bass"
    assert res["model_id"] == "bass_diffusion"
    assert res["data"]["cumulative_adopters"]["provenance_class"] == "calculated"

    cum = res["data"]["cumulative_adopters"]["value"]
    new_ad = res["data"]["new_adopters"]["value"]

    assert len(cum) == horizon + 1
    assert len(new_ad) == horizon

    # Period 0 checks
    assert math.isclose(cum[0], 0.0, abs_tol=1e-10)
    assert math.isclose(new_ad[0], 300.0, abs_tol=1e-10)  # p * M = 0.03 * 10000
    assert math.isclose(cum[1], 300.0, abs_tol=1e-10)

    # Period 1 checks: (0.03 + 0.38 * 300 / 10000) * (10000 - 300) = 0.0414 * 9700 = 401.58
    assert math.isclose(new_ad[1], 401.58, abs_tol=1e-10)
    assert math.isclose(cum[2], 701.58, abs_tol=1e-10)

    # Monotonicity and boundary checks
    for t in range(horizon):
        assert new_ad[t] >= 0.0
        assert cum[t + 1] >= cum[t]
        assert cum[t + 1] <= M

    assert res["metadata"]["seed"] == "not_applicable"
    assert res["metadata"]["horizon"] == horizon
    assert res["metadata"]["market_potential"] == M


def test_bass_pure_innovation_exponential_approach() -> None:
    # When q = 0, discrete dynamics: N(t) = M * (1 - (1 - p)^t)
    M = 5000.0
    p = 0.05
    q = 0.0
    horizon = 15

    res = simulate_bass_diffusion(M, p, q, initial_adopters=0.0, horizon=horizon)
    cum = res["data"]["cumulative_adopters"]["value"]

    for t in range(horizon + 1):
        expected = M * (1.0 - (1.0 - p) ** t)
        assert math.isclose(cum[t], expected, abs_tol=1e-8)


def test_bass_peak_adoption_detection() -> None:
    M = 100000.0
    p = 0.02
    q = 0.40
    horizon = 25

    res = simulate_bass_diffusion(M, p, q, initial_adopters=0.0, horizon=horizon)
    new_ad = res["data"]["new_adopters"]["value"]

    peak_period = res["data"]["peak_adoption_period"]["value"]
    peak_rate = res["data"]["peak_adoption_rate"]["value"]

    assert peak_period == new_ad.index(max(new_ad))
    assert math.isclose(peak_rate, max(new_ad), abs_tol=1e-10)


def test_bass_result_schema_contract() -> None:
    res = simulate_bass_diffusion(10000.0, 0.03, 0.38, horizon=10)
    issues = validate_contract(res)
    assert not issues, f"Contract validation failed: {issues}"
