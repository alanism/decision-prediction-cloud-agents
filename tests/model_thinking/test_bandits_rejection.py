from __future__ import annotations

from pathlib import Path

from capital_decision_lab.calculations.bandits import analyze_bandit_input, simulate_bernoulli_bandit
from capital_decision_lab.contracts.canonical import contract_payload_hash

ROOT = Path(__file__).resolve().parents[2]


def test_bandit_rejects_arm_count_bounds() -> None:
    # Less than 2 arms
    res1 = simulate_bernoulli_bandit([0.5])
    assert res1["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "arm count must be between 2 and 64" in res1["data"]["total_reward"]["reason"]

    # More than 64 arms
    res65 = simulate_bernoulli_bandit([0.5] * 65)
    assert res65["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "arm count must be between 2 and 64" in res65["data"]["total_reward"]["reason"]


def test_bandit_rejects_invalid_arm_probabilities() -> None:
    # Negative
    res_neg = simulate_bernoulli_bandit([-0.1, 0.5])
    assert res_neg["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "arm probabilities must be finite numbers between 0 and 1" in res_neg["data"]["total_reward"]["reason"]

    # Exceeding 1.0
    res_over = simulate_bernoulli_bandit([1.2, 0.5])
    assert res_over["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "arm probabilities must be finite numbers between 0 and 1" in res_over["data"]["total_reward"]["reason"]

    # Nonfinite
    res_nan = simulate_bernoulli_bandit([float("nan"), 0.5])
    assert res_nan["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "arm probabilities must be finite numbers between 0 and 1" in res_nan["data"]["total_reward"]["reason"]

    # Boolean
    res_bool = simulate_bernoulli_bandit([True, 0.5])  # type: ignore
    assert res_bool["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "arm probabilities must be finite numbers between 0 and 1" in res_bool["data"]["total_reward"]["reason"]


def test_bandit_rejects_horizon_bounds() -> None:
    res_zero = simulate_bernoulli_bandit([0.2, 0.8], horizon=0)
    assert res_zero["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "horizon must be between 1 and 100000" in res_zero["data"]["total_reward"]["reason"]

    res_huge = simulate_bernoulli_bandit([0.2, 0.8], horizon=200000)
    assert res_huge["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "horizon must be between 1 and 100000" in res_huge["data"]["total_reward"]["reason"]


def test_bandit_rejects_initial_pull_bounds() -> None:
    # initial pulls < 1
    res_low = simulate_bernoulli_bandit([0.2, 0.8], initial_pulls_per_arm=0)
    assert res_low["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "initial pulls per arm must be at least 1" in res_low["data"]["total_reward"]["reason"]

    # initial pulls * K > horizon
    res_over = simulate_bernoulli_bandit([0.2, 0.8, 0.5], horizon=50, initial_pulls_per_arm=20)
    assert res_over["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "total initial pulls cannot exceed horizon" in res_over["data"]["total_reward"]["reason"]


def test_bandit_rejects_unknown_policy() -> None:
    # Must reject unknown policies (not silently substitute UCB1/Thompson)
    res_ucb = simulate_bernoulli_bandit([0.2, 0.8], policy="ucb1")
    assert res_ucb["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "policy must be one of ['greedy', 'sample_then_greedy', 'adaptive_epsilon']" in res_ucb["data"]["total_reward"]["reason"]

    res_thompson = simulate_bernoulli_bandit([0.2, 0.8], policy="thompson_sampling")
    assert res_thompson["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "policy must be one of ['greedy', 'sample_then_greedy', 'adaptive_epsilon']" in res_thompson["data"]["total_reward"]["reason"]


def test_bandit_rejects_untrusted_input_envelope() -> None:
    model_input = {
        "contract_version": "nhi.model_input.v1",
        "model_id": "bernoulli_bandit",
        "model_family": "bandit",
        "model_version": "1.0.0",
        "input_trust_class": "untrusted_external",
        "parameters": {
            "arm_probabilities": [0.2, 0.8],
            "horizon": 100,
            "policy": "sample_then_greedy",
        },
    }
    model_input["canonical_hash"] = contract_payload_hash(model_input)
    res = analyze_bandit_input(model_input)
    assert res["data"]["total_reward"]["provenance_class"] == "unavailable"
    assert "untrusted input requires user confirmation" in res["data"]["total_reward"]["reason"]
