from __future__ import annotations

import math
from pathlib import Path

from capital_decision_lab.calculations.markov import compute_stationary_distribution
from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract

ROOT = Path(__file__).resolve().parents[2]


def test_markov_grounded_two_state_analytical_solution() -> None:
    # Grounded 2-state case from Page Many-Model framework:
    # State 0: recession, State 1: expansion
    # P(0 -> 0) = 0.9, P(0 -> 1) = 0.1
    # P(1 -> 0) = 0.3, P(1 -> 1) = 0.7
    # Analytical stationary: pi_0 = 0.3/(0.1+0.3) = 0.75, pi_1 = 0.1/(0.1+0.3) = 0.25
    states = ["recession", "expansion"]
    matrix = [
        [0.9, 0.1],
        [0.3, 0.7],
    ]
    res = compute_stationary_distribution(states, matrix, transition_rule_fixed=True)

    assert res["contract_version"] == "nhi.model_result.v1"
    assert res["model_family"] == "markov"
    assert res["model_id"] == "markov_regime"
    assert res["data"]["stationary_distribution"]["provenance_class"] == "calculated"

    dist = res["data"]["stationary_distribution"]["value"]
    assert math.isclose(dist["recession"], 0.75, rel_tol=0.0, abs_tol=1e-10)
    assert math.isclose(dist["expansion"], 0.25, rel_tol=0.0, abs_tol=1e-10)
    assert math.isclose(dist["recession"] + dist["expansion"], 1.0, rel_tol=0.0, abs_tol=1e-12)

    assert res["data"]["is_irreducible"]["value"] is True
    assert res["data"]["is_aperiodic"]["value"] is True
    assert res["metadata"]["seed"] == "not_applicable"


def test_markov_three_state_convergence() -> None:
    states = ["bull", "neutral", "bear"]
    matrix = [
        [0.7, 0.2, 0.1],
        [0.3, 0.4, 0.3],
        [0.2, 0.3, 0.5],
    ]
    res = compute_stationary_distribution(states, matrix, transition_rule_fixed=True)
    dist = res["data"]["stationary_distribution"]["value"]

    # Verify stationary property: pi * T = pi
    pi = [dist["bull"], dist["neutral"], dist["bear"]]
    for j in range(3):
        col_dot = sum(pi[i] * matrix[i][j] for i in range(3))
        assert math.isclose(pi[j], col_dot, rel_tol=0.0, abs_tol=1e-10)
    assert math.isclose(sum(pi), 1.0, rel_tol=0.0, abs_tol=1e-12)


def test_markov_result_schema_contract() -> None:
    states = ["state_a", "state_b"]
    matrix = [
        [0.8, 0.2],
        [0.4, 0.6],
    ]
    res = compute_stationary_distribution(states, matrix, transition_rule_fixed=True)
    issues = validate_contract(res)
    assert not issues, f"Contract validation failed: {issues}"
