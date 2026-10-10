from __future__ import annotations

import math
from pathlib import Path

from capital_decision_lab.calculations.power_law import (
    analyze_power_law_input,
    fit_power_law_tail,
)
from capital_decision_lab.contracts.canonical import contract_payload_hash

ROOT = Path(__file__).resolve().parents[2]


def test_power_law_rejects_undersized_sample() -> None:
    obs = [10.0 + i for i in range(49)]  # 49 < 50 minimum
    res = fit_power_law_tail(obs, 10.0)
    assert res["data"]["alpha"]["provenance_class"] == "unavailable"
    assert "observations count must be between 50 and 10000" in res["data"]["alpha"]["reason"]


def test_power_law_rejects_oversized_sample() -> None:
    obs = [10.0 + (i % 100) for i in range(10_001)]  # 10001 > 10000 cap
    res = fit_power_law_tail(obs, 10.0)
    assert res["data"]["alpha"]["provenance_class"] == "unavailable"
    assert "observations count must be between 50 and 10000" in res["data"]["alpha"]["reason"]


def test_power_law_rejects_nonpositive_xmin() -> None:
    obs = [10.0 + i for i in range(60)]
    res = fit_power_law_tail(obs, -5.0)
    assert res["data"]["alpha"]["provenance_class"] == "unavailable"
    assert "xmin must be a positive finite number" in res["data"]["alpha"]["reason"]


def test_power_law_rejects_nonfinite_observations() -> None:
    obs = [10.0 + i for i in range(59)] + [float("nan")]
    res = fit_power_law_tail(obs, 10.0)
    assert res["data"]["alpha"]["provenance_class"] == "unavailable"
    assert "observations must be positive finite numbers" in res["data"]["alpha"]["reason"]


def test_power_law_rejects_observations_below_xmin() -> None:
    obs = [5.0] + [10.0 + i for i in range(59)]  # 5.0 < 10.0
    res = fit_power_law_tail(obs, 10.0)
    assert res["data"]["alpha"]["provenance_class"] == "unavailable"
    assert "observations must be greater than or equal to xmin" in res["data"]["alpha"]["reason"]


def test_power_law_rejects_constant_observations() -> None:
    obs = [10.0 for _ in range(60)]  # All identical to xmin -> sum(log(x/xmin)) == 0
    res = fit_power_law_tail(obs, 10.0)
    assert res["data"]["alpha"]["provenance_class"] == "unavailable"
    assert "observations must have positive variance above xmin" in res["data"]["alpha"]["reason"]


def test_power_law_rejects_untrusted_input_envelope() -> None:
    model_input = {
        "contract_version": "nhi.model_input.v1",
        "model_id": "power_law_tail",
        "model_family": "power_law",
        "model_version": "1.0.0",
        "input_trust_class": "untrusted_external",  # External untrusted
        "parameters": {
            "xmin": 10.0,
            "observations": [10.0 + i for i in range(60)],
        },
    }
    model_input["canonical_hash"] = contract_payload_hash(model_input)
    res = analyze_power_law_input(model_input)
    assert res["data"]["alpha"]["provenance_class"] == "unavailable"
    assert "untrusted input requires user confirmation" in res["data"]["alpha"]["reason"]


def test_power_law_deterministic_seed_replay() -> None:
    obs = [10.0 + i * 0.5 for i in range(60)]
    res1 = fit_power_law_tail(obs, 10.0, bootstrap_trials=100, seed=12345)
    res2 = fit_power_law_tail(obs, 10.0, bootstrap_trials=100, seed=12345)
    assert res1["canonical_hash"] == res2["canonical_hash"]
    assert res1["data"]["diagnostic_p_value"]["value"] == res2["data"]["diagnostic_p_value"]["value"]
