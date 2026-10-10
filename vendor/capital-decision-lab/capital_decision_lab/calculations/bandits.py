"""Bernoulli multi-armed bandit simulation engine."""

from __future__ import annotations

import hashlib
import math
import random
from typing import Any

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import unavailable_result
from capital_decision_lab.evidence.common import atom

MIN_ARMS = 2
MAX_ARMS = 64
MIN_HORIZON = 1
MAX_HORIZON = 100_000
SUPPORTED_POLICIES = {"greedy", "sample_then_greedy", "adaptive_epsilon"}


def _derive_canonical_bandit_seed(
    arms: list[float],
    horizon: int,
    policy: str,
    initial_pulls: int,
    eps_0: float,
    eps_min: float,
) -> int:
    hasher = hashlib.sha256()
    hasher.update(f"{horizon}:{policy}:{initial_pulls}:{eps_0:.6e}:{eps_min:.6e}:".encode("utf-8"))
    for p in arms:
        hasher.update(f"{p:.8e},".encode("utf-8"))
    return int(hasher.hexdigest()[:16], 16)


def _unavailable_bandit_result(reason: str) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "contract_version": "nhi.model_result.v1",
        "result_id": "bandit_unavailable",
        "model_id": "bernoulli_bandit",
        "model_family": "bandit",
        "model_version": "1.0.0",
        "input_hash": "0" * 64,
        "data": {
            "total_reward": unavailable_result(reason, unit="count"),
            "cumulative_regret": unavailable_result(reason, unit="expected_loss"),
            "arm_pulls": unavailable_result(reason, unit="pulls"),
            "arm_rewards": unavailable_result(reason, unit="rewards"),
            "estimated_arm_means": unavailable_result(reason, unit="probability"),
            "best_arm_index": unavailable_result(reason, unit="arm_index"),
        },
        "metadata": {
            "algorithm_version": "bernoulli_bandit_v1",
            "seed": "not_applicable",
            "horizon": 0,
            "policy": "none",
        },
        "limitations": [
            "Bandit simulation unavailable under supplied parameters or validation failure."
        ],
    }
    doc["canonical_hash"] = contract_payload_hash(doc)
    return doc


def simulate_bernoulli_bandit(
    arm_probabilities: list[float],
    *,
    horizon: int = 1000,
    policy: str = "sample_then_greedy",
    initial_pulls_per_arm: int = 10,
    epsilon_0: float = 1.0,
    epsilon_min: float = 0.01,
    seed: int | None = None,
) -> dict[str, Any]:
    """Execute deterministic Bernoulli multi-armed bandit simulation."""
    if not isinstance(arm_probabilities, list):
        return _unavailable_bandit_result("arm probabilities must be a list")

    k = len(arm_probabilities)
    if k < MIN_ARMS or k > MAX_ARMS:
        return _unavailable_bandit_result(f"arm count must be between {MIN_ARMS} and {MAX_ARMS}")

    p_arms: list[float] = []
    for p in arm_probabilities:
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(float(p)) or float(p) < 0.0 or float(p) > 1.0:
            return _unavailable_bandit_result("arm probabilities must be finite numbers between 0 and 1")
        p_arms.append(float(p))

    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < MIN_HORIZON or horizon > MAX_HORIZON:
        return _unavailable_bandit_result(f"horizon must be between {MIN_HORIZON} and {MAX_HORIZON}")

    if isinstance(initial_pulls_per_arm, bool) or not isinstance(initial_pulls_per_arm, int) or initial_pulls_per_arm < 1:
        return _unavailable_bandit_result("initial pulls per arm must be at least 1")

    if initial_pulls_per_arm * k > horizon:
        return _unavailable_bandit_result("total initial pulls cannot exceed horizon")

    if policy not in SUPPORTED_POLICIES:
        return _unavailable_bandit_result("policy must be one of ['greedy', 'sample_then_greedy', 'adaptive_epsilon']")

    if seed is None:
        effective_seed = _derive_canonical_bandit_seed(p_arms, horizon, policy, initial_pulls_per_arm, epsilon_0, epsilon_min)
    else:
        effective_seed = int(seed)

    rng = random.Random(effective_seed)

    pulls = [0] * k
    rewards = [0] * k
    total_reward = 0

    # Phase 1: Round-robin initial exploration
    for i in range(k):
        for _ in range(initial_pulls_per_arm):
            r = 1 if rng.random() < p_arms[i] else 0
            pulls[i] += 1
            rewards[i] += r
            total_reward += r

    # Determine fixed best arm for sample_then_greedy
    if policy == "sample_then_greedy":
        best_fixed_arm = 0
        best_fixed_mean = -1.0
        for i in range(k):
            m = rewards[i] / pulls[i]
            if m > best_fixed_mean:
                best_fixed_mean = m
                best_fixed_arm = i

    # Phase 2: Main policy horizon
    for t in range(initial_pulls_per_arm * k, horizon):
        if policy == "greedy":
            # Greedy choice with lowest index tie-breaking
            chosen_arm = 0
            best_mean = -1.0
            for i in range(k):
                m = rewards[i] / pulls[i]
                if m > best_mean:
                    best_mean = m
                    chosen_arm = i
        elif policy == "sample_then_greedy":
            chosen_arm = best_fixed_arm
        elif policy == "adaptive_epsilon":
            eps_t = max(epsilon_min, epsilon_0 / math.sqrt(float(t + 1)))
            is_explore = rng.random() < eps_t
            if is_explore:
                chosen_arm = rng.randrange(k)
            else:
                chosen_arm = 0
                best_mean = -1.0
                for i in range(k):
                    m = rewards[i] / pulls[i]
                    if m > best_mean:
                        best_mean = m
                        chosen_arm = i

        r = 1 if rng.random() < p_arms[chosen_arm] else 0
        pulls[chosen_arm] += 1
        rewards[chosen_arm] += r
        total_reward += r

    est_means = [rewards[i] / pulls[i] for i in range(k)]
    best_arm_idx = est_means.index(max(est_means))
    max_p = max(p_arms)
    cumulative_regret = float(horizon * max_p - total_reward)

    input_hash = hashlib.sha256(f"{p_arms}:{horizon}:{policy}:{initial_pulls_per_arm}:{effective_seed}".encode("utf-8")).hexdigest()

    doc: dict[str, Any] = {
        "contract_version": "nhi.model_result.v1",
        "result_id": f"bandit_res_{input_hash[:16]}",
        "model_id": "bernoulli_bandit",
        "model_family": "bandit",
        "model_version": "1.0.0",
        "input_hash": input_hash,
        "data": {
            "total_reward": atom(total_reward, "modeled", formula_ref="bandit.bernoulli_simulation.v1", unit="count"),
            "cumulative_regret": atom(cumulative_regret, "modeled", formula_ref="bandit.pseudo_regret.v1", unit="expected_loss"),
            "arm_pulls": atom(pulls, "modeled", unit="pulls"),
            "arm_rewards": atom(rewards, "modeled", unit="rewards"),
            "estimated_arm_means": atom(est_means, "modeled", unit="probability"),
            "best_arm_index": atom(best_arm_idx, "modeled", unit="arm_index"),
        },
        "metadata": {
            "algorithm_version": "bernoulli_bandit_v1",
            "seed": effective_seed,
            "horizon": horizon,
            "policy": policy,
            "initial_pulls_per_arm": initial_pulls_per_arm,
            "epsilon_0": epsilon_0,
            "epsilon_min": epsilon_min,
        },
        "limitations": [
            "Bandit simulation results depend on stationary arm reward distributions and pseudo-random seed."
        ],
    }
    doc["canonical_hash"] = contract_payload_hash(doc)
    return doc


def analyze_bandit_input(model_input: dict) -> dict[str, Any]:
    """Execute Bernoulli bandit simulation over an nhi.model_input.v1 envelope."""
    trust_class = model_input.get("input_trust_class")
    if trust_class == "untrusted_external":
        return _unavailable_bandit_result("untrusted input requires user confirmation")

    params = model_input.get("parameters", {})
    arms = params.get("arm_probabilities", [])
    horizon = params.get("horizon", 1000)
    policy = params.get("policy", "sample_then_greedy")
    initial_pulls = params.get("initial_pulls_per_arm", 10)
    eps_0 = params.get("epsilon_0", 1.0)
    eps_min = params.get("epsilon_min", 0.01)
    seed = params.get("seed")

    return simulate_bernoulli_bandit(
        arms,
        horizon=horizon,
        policy=policy,
        initial_pulls_per_arm=initial_pulls,
        epsilon_0=eps_0,
        epsilon_min=eps_min,
        seed=seed,
    )
