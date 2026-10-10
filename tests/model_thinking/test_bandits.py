from __future__ import annotations

import math
from pathlib import Path

from capital_decision_lab.calculations.bandits import simulate_bernoulli_bandit
from capital_decision_lab.contracts.validation import validate_contract

ROOT = Path(__file__).resolve().parents[2]


def test_bandit_deterministic_seed_replay() -> None:
    arms = [0.2, 0.5, 0.8]
    res1 = simulate_bernoulli_bandit(arms, horizon=500, policy="sample_then_greedy", initial_pulls_per_arm=20, seed=12345)
    res2 = simulate_bernoulli_bandit(arms, horizon=500, policy="sample_then_greedy", initial_pulls_per_arm=20, seed=12345)

    assert res1["contract_version"] == "nhi.model_result.v1"
    assert res1["model_family"] == "bandit"
    assert res1["model_id"] == "bernoulli_bandit"
    assert res1["data"]["total_reward"]["provenance_class"] == "modeled"

    r1 = res1["data"]["total_reward"]["value"]
    r2 = res2["data"]["total_reward"]["value"]
    assert r1 == r2

    pulls1 = res1["data"]["arm_pulls"]["value"]
    pulls2 = res2["data"]["arm_pulls"]["value"]
    assert pulls1 == pulls2
    assert sum(pulls1) == 500

    regret1 = res1["data"]["cumulative_regret"]["value"]
    regret2 = res2["data"]["cumulative_regret"]["value"]
    assert math.isclose(regret1, regret2, abs_tol=1e-10)
    assert math.isclose(regret1, 500 * max(arms) - r1, abs_tol=1e-10)


def test_bandit_greedy_and_adaptive_policies() -> None:
    arms = [0.3, 0.7]
    res_greedy = simulate_bernoulli_bandit(arms, horizon=200, policy="greedy", initial_pulls_per_arm=10, seed=999)
    assert res_greedy["data"]["arm_pulls"]["provenance_class"] == "modeled"
    assert sum(res_greedy["data"]["arm_pulls"]["value"]) == 200

    res_adaptive = simulate_bernoulli_bandit(
        arms,
        horizon=300,
        policy="adaptive_epsilon",
        initial_pulls_per_arm=5,
        epsilon_0=0.8,
        epsilon_min=0.05,
        seed=999,
    )
    assert res_adaptive["data"]["arm_pulls"]["provenance_class"] == "modeled"
    assert sum(res_adaptive["data"]["arm_pulls"]["value"]) == 300


def test_bandit_canonical_derived_seed_when_none() -> None:
    arms = [0.1, 0.4, 0.9]
    res1 = simulate_bernoulli_bandit(arms, horizon=100, seed=None)
    res2 = simulate_bernoulli_bandit(arms, horizon=100, seed=None)

    assert res1["metadata"]["seed"] != "not_applicable"
    assert res1["metadata"]["seed"] == res2["metadata"]["seed"]
    assert res1["data"]["total_reward"]["value"] == res2["data"]["total_reward"]["value"]


def test_bandit_result_schema_contract() -> None:
    res = simulate_bernoulli_bandit([0.2, 0.6], horizon=100, seed=42)
    issues = validate_contract(res)
    assert not issues, f"Contract validation failed: {issues}"
