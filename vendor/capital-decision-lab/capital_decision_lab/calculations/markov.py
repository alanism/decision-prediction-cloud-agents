"""Markov regime and stationary distribution diagnostic."""

from __future__ import annotations

import hashlib
import math
from typing import Any

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import unavailable_result
from capital_decision_lab.evidence.common import atom

MIN_STATES = 2
MAX_STATES = 64
ROW_SUM_TOLERANCE = 1e-12
CONVERGENCE_TOLERANCE = 1e-12
MAX_ITERATIONS_CAP = 100_000


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)


def _check_irreducibility(n: int, matrix: list[list[float]]) -> bool:
    """Check if transition graph is strongly connected (irreducible)."""
    for start in range(n):
        visited = set()
        queue = [start]
        visited.add(start)
        while queue:
            curr = queue.pop(0)
            for neighbor in range(n):
                if matrix[curr][neighbor] > 1e-12 and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        if len(visited) != n:
            return False
    return True


def _check_aperiodicity(n: int, matrix: list[list[float]]) -> bool:
    """Check if strongly connected chain is aperiodic (period == 1)."""
    # Using BFS spanning tree cycle length theorem:
    # In strongly connected digraph, period equals gcd of |L(u) - L(v) + 1| across all edges (u, v).
    levels = [-1] * n
    levels[0] = 0
    queue = [0]
    while queue:
        u = queue.pop(0)
        for v in range(n):
            if matrix[u][v] > 1e-12 and levels[v] == -1:
                levels[v] = levels[u] + 1
                queue.append(v)

    g = 0
    for u in range(n):
        for v in range(n):
            if matrix[u][v] > 1e-12:
                cycle_len = abs(levels[u] - levels[v] + 1)
                g = _gcd(g, cycle_len)
                if g == 1:
                    return True
    return g == 1


def _unavailable_markov_result(reason: str, states_count: int = 0) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "contract_version": "nhi.model_result.v1",
        "result_id": "markov_regime_unavailable",
        "model_id": "markov_regime",
        "model_family": "markov",
        "model_version": "1.0.0",
        "input_hash": "0" * 64,
        "data": {
            "stationary_distribution": unavailable_result(reason),
            "is_irreducible": unavailable_result(reason),
            "is_aperiodic": unavailable_result(reason),
            "iterations_to_converge": unavailable_result(reason, unit="iterations"),
            "l1_residual": unavailable_result(reason, unit="l1_norm"),
        },
        "metadata": {
            "algorithm_version": "markov_power_iteration_v1",
            "seed": "not_applicable",
            "states_count": states_count,
            "max_iterations": MAX_ITERATIONS_CAP,
        },
        "limitations": [
            "Stationary distribution unavailable under supplied parameters or chain validation failure."
        ],
    }
    doc["canonical_hash"] = contract_payload_hash(doc)
    return doc


def compute_stationary_distribution(
    states: list[str],
    transition_matrix: list[list[float]],
    *,
    orientation: str = "row_from_state",
    transition_rule_fixed: bool = True,
    max_iterations: int = MAX_ITERATIONS_CAP,
    tolerance: float = CONVERGENCE_TOLERANCE,
) -> dict[str, Any]:
    """Calculate exact stationary distribution vector for an ergodic Markov chain."""
    if not transition_rule_fixed:
        return _unavailable_markov_result("transition rule must be asserted fixed and trusted")

    if orientation != "row_from_state":
        return _unavailable_markov_result("orientation must be row_from_state")

    if not isinstance(states, list):
        return _unavailable_markov_result("states must be a list of string identifiers")

    n = len(states)
    if n < MIN_STATES or n > MAX_STATES:
        return _unavailable_markov_result(f"states count must be between {MIN_STATES} and {MAX_STATES}")

    if len(set(states)) != n or any(not isinstance(s, str) or not s.strip() for s in states):
        return _unavailable_markov_result("state names must be unique non-empty strings")

    if not isinstance(transition_matrix, list) or len(transition_matrix) != n:
        return _unavailable_markov_result("transition matrix must be square matching states length", states_count=n)

    mat_floats: list[list[float]] = []
    for row in transition_matrix:
        if not isinstance(row, list) or len(row) != n:
            return _unavailable_markov_result("transition matrix must be square matching states length", states_count=n)
        row_floats: list[float] = []
        for x in row:
            if (
                not isinstance(x, (int, float))
                or isinstance(x, bool)
                or not math.isfinite(float(x))
                or float(x) < 0.0
                or float(x) > 1.0
            ):
                return _unavailable_markov_result("matrix entries must be finite numbers between 0 and 1", states_count=n)
            row_floats.append(float(x))
        row_sum = sum(row_floats)
        if not math.isclose(row_sum, 1.0, rel_tol=0.0, abs_tol=ROW_SUM_TOLERANCE):
            return _unavailable_markov_result("each matrix row must sum to 1.0", states_count=n)
        mat_floats.append(row_floats)

    # Check irreducibility
    if not _check_irreducibility(n, mat_floats):
        return _unavailable_markov_result("markov chain must be irreducible", states_count=n)

    # Check aperiodicity
    if not _check_aperiodicity(n, mat_floats):
        return _unavailable_markov_result("markov chain must be aperiodic", states_count=n)

    # Power iteration with uniform initialization
    pi = [1.0 / float(n)] * n
    converged = False
    iterations_run = 0
    final_residual = 0.0

    for step in range(1, max_iterations + 1):
        pi_next = [0.0] * n
        for j in range(n):
            pi_next[j] = sum(pi[i] * mat_floats[i][j] for i in range(n))

        # L1 norm difference
        l1_diff = sum(abs(pi_next[j] - pi[j]) for j in range(n))
        pi = pi_next
        iterations_run = step
        final_residual = l1_diff

        if l1_diff <= tolerance:
            converged = True
            break

    # Normalize stationary vector
    sum_pi = sum(pi)
    pi_normalized = [p / sum_pi for p in pi]
    dist_map = {states[i]: pi_normalized[i] for i in range(n)}

    hasher = hashlib.sha256()
    for s in states:
        hasher.update(s.encode("utf-8"))
    for row in mat_floats:
        for val in row:
            hasher.update(f"{val:.12e},".encode("utf-8"))
    input_hash = hasher.hexdigest()

    doc: dict[str, Any] = {
        "contract_version": "nhi.model_result.v1",
        "result_id": f"markov_regime_res_{input_hash[:16]}",
        "model_id": "markov_regime",
        "model_family": "markov",
        "model_version": "1.0.0",
        "input_hash": input_hash,
        "data": {
            "stationary_distribution": atom(dist_map, "calculated", formula_ref="markov.power_iteration.v1"),
            "is_irreducible": atom(True, "calculated", formula_ref="markov.irreducibility.v1"),
            "is_aperiodic": atom(True, "calculated", formula_ref="markov.aperiodicity.v1"),
            "iterations_to_converge": atom(iterations_run, "calculated", unit="iterations"),
            "l1_residual": atom(final_residual, "calculated", unit="l1_norm"),
        },
        "metadata": {
            "algorithm_version": "markov_power_iteration_v1",
            "seed": "not_applicable",
            "states_count": n,
            "max_iterations": max_iterations,
        },
        "limitations": [
            "Stationary distribution assumes transition probabilities remain constant over the long run."
        ],
    }
    doc["canonical_hash"] = contract_payload_hash(doc)
    return doc


def analyze_markov_input(model_input: dict) -> dict[str, Any]:
    """Execute Markov stationary distribution calculation over an nhi.model_input.v1 envelope."""
    trust_class = model_input.get("input_trust_class")
    if trust_class == "untrusted_external":
        return _unavailable_markov_result("untrusted input requires user confirmation")

    params = model_input.get("parameters", {})
    states = params.get("states")
    matrix = params.get("transition_matrix")
    orientation = params.get("orientation", "row_from_state")
    fixed_rule = params.get("transition_rule_fixed", True)

    return compute_stationary_distribution(
        states,
        matrix,
        orientation=orientation,
        transition_rule_fixed=fixed_rule,
    )
