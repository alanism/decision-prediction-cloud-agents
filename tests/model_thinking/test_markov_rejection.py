from __future__ import annotations

import math
from pathlib import Path

from capital_decision_lab.calculations.markov import (
    analyze_markov_input,
    compute_stationary_distribution,
)
from capital_decision_lab.contracts.canonical import contract_payload_hash

ROOT = Path(__file__).resolve().parents[2]


def test_markov_rejects_non_square_matrix() -> None:
    states = ["a", "b"]
    matrix = [[0.5, 0.5, 0.0], [0.5, 0.5, 0.0]]  # 2x3
    res = compute_stationary_distribution(states, matrix)
    assert res["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "transition matrix must be square matching states length" in res["data"]["stationary_distribution"]["reason"]


def test_markov_rejects_state_dimension_bounds() -> None:
    # Less than 2 states
    res1 = compute_stationary_distribution(["single"], [[1.0]])
    assert res1["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "states count must be between 2 and 64" in res1["data"]["stationary_distribution"]["reason"]

    # More than 64 states
    states_large = [f"s_{i}" for i in range(65)]
    matrix_large = [[1.0 / 65.0] * 65 for _ in range(65)]
    res2 = compute_stationary_distribution(states_large, matrix_large)
    assert res2["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "states count must be between 2 and 64" in res2["data"]["stationary_distribution"]["reason"]


def test_markov_rejects_row_sum_violation() -> None:
    states = ["a", "b"]
    # Transposed/column stochastic: col sums are 1.0, but row 0 sum is 1.4
    matrix = [[0.9, 0.5], [0.1, 0.5]]
    res = compute_stationary_distribution(states, matrix)
    assert res["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "each matrix row must sum to 1.0" in res["data"]["stationary_distribution"]["reason"]


def test_markov_rejects_negative_or_nonfinite_probabilities() -> None:
    states = ["a", "b"]
    matrix_neg = [[1.2, -0.2], [0.5, 0.5]]
    res_neg = compute_stationary_distribution(states, matrix_neg)
    assert res_neg["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "matrix entries must be finite numbers between 0 and 1" in res_neg["data"]["stationary_distribution"]["reason"]

    matrix_nan = [[float("nan"), float("nan")], [0.5, 0.5]]
    res_nan = compute_stationary_distribution(states, matrix_nan)
    assert res_nan["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "matrix entries must be finite numbers between 0 and 1" in res_nan["data"]["stationary_distribution"]["reason"]


def test_markov_rejects_booleans_in_matrix() -> None:
    states = ["a", "b"]
    matrix = [[True, False], [0.5, 0.5]]
    res = compute_stationary_distribution(states, matrix)
    assert res["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "matrix entries must be finite numbers between 0 and 1" in res["data"]["stationary_distribution"]["reason"]


def test_markov_rejects_periodic_chain() -> None:
    # Deterministic 2-state oscillation: 0 -> 1 -> 0 -> 1 ...
    states = ["a", "b"]
    matrix = [[0.0, 1.0], [1.0, 0.0]]
    res = compute_stationary_distribution(states, matrix)
    assert res["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "markov chain must be aperiodic" in res["data"]["stationary_distribution"]["reason"]


def test_markov_rejects_reducible_chain() -> None:
    # Absorbing state: state 0 goes to 1, but state 1 cannot return to 0
    states = ["transient", "absorbing"]
    matrix = [[0.0, 1.0], [0.0, 1.0]]
    res = compute_stationary_distribution(states, matrix)
    assert res["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "markov chain must be irreducible" in res["data"]["stationary_distribution"]["reason"]


def test_markov_rejects_untrusted_rule_assertion() -> None:
    states = ["a", "b"]
    matrix = [[0.8, 0.2], [0.4, 0.6]]
    # transition_rule_fixed = False
    res = compute_stationary_distribution(states, matrix, transition_rule_fixed=False)
    assert res["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "transition rule must be asserted fixed and trusted" in res["data"]["stationary_distribution"]["reason"]


def test_markov_rejects_untrusted_input_envelope() -> None:
    model_input = {
        "contract_version": "nhi.model_input.v1",
        "model_id": "markov_regime",
        "model_family": "markov",
        "model_version": "1.0.0",
        "input_trust_class": "untrusted_external",
        "parameters": {
            "states": ["a", "b"],
            "transition_matrix": [[0.8, 0.2], [0.4, 0.6]],
            "transition_rule_fixed": True,
        },
    }
    model_input["canonical_hash"] = contract_payload_hash(model_input)
    res = analyze_markov_input(model_input)
    assert res["data"]["stationary_distribution"]["provenance_class"] == "unavailable"
    assert "untrusted input requires user confirmation" in res["data"]["stationary_distribution"]["reason"]
