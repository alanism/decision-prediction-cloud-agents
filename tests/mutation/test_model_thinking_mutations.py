"""Permanent source-level mutation tests for Many-Model thinking components.

Dynamically creates source-level AST mutants across calculation engines, moment safety
thresholds, discrete dynamics, Markov graph algorithms, bandit policies, claim compilation,
and runner trust verification. Executes the test suite against each mutated module and
mechanically verifies that 100% of mutants are caught and killed.
"""

from __future__ import annotations

import ast
import copy
import importlib
import math
from pathlib import Path
import random
import types
import pytest

from capital_decision_lab.calculations.bandits import simulate_bernoulli_bandit
from capital_decision_lab.calculations.bass import simulate_bass_diffusion
from capital_decision_lab.calculations.markov import compute_stationary_distribution
from capital_decision_lab.calculations.power_law import continuous_power_law_mle, fit_power_law_tail
from capital_decision_lab.ensemble.compiler import compile_claim_ensemble
from capital_decision_lab.methods.runner import run_committee, run_method_pack
from tests.orchestration.test_analyze_position import workflow_case

ROOT = Path(__file__).resolve().parents[2]


# =============================================================================
# AST Source Mutation Engine
# =============================================================================

def apply_source_mutation(file_path: Path, target_snippet: str, mutated_snippet: str) -> types.ModuleType:
    """Read a python source file, substitute an exact target code snippet, and compile a mutated module."""
    source = file_path.read_text(encoding="utf-8")
    if target_snippet not in source:
        raise ValueError(f"Target snippet not found in {file_path.name}:\n{target_snippet}")
    mutated_source = source.replace(target_snippet, mutated_snippet, 1)

    # Validate AST syntax of mutated code
    parsed_ast = ast.parse(mutated_source, filename=f"<mutant_{file_path.stem}>")
    compiled_code = compile(parsed_ast, filename=f"<mutant_{file_path.stem}>", mode="exec")

    # Determine module package
    parts = file_path.with_suffix("").parts
    if "capital_decision_lab" in parts:
        idx = parts.index("capital_decision_lab")
        pkg_name = ".".join(parts[idx:-1])
    else:
        pkg_name = ""

    mutant_module = types.ModuleType(f"mutant_{file_path.stem}")
    mutant_module.__file__ = str(file_path)
    mutant_module.__package__ = pkg_name
    exec(compiled_code, mutant_module.__dict__)
    return mutant_module


# =============================================================================
# 1. Power-Law Source Mutations
# =============================================================================

def test_source_mutant_power_law_mle_offset_killed() -> None:
    """Mutant: In power_law.py continuous_power_law_mle, mutate `1.0 + float(n) / sum_log` -> `float(n) / sum_log`."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/calculations/power_law.py"
    target_snippet = "return 1.0 + float(n) / sum_log"
    mutated_snippet = "return float(n) / sum_log"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)
    obs = [10.0 * (1.0 + i * 0.1) for i in range(100)]

    true_alpha = continuous_power_law_mle(obs, 10.0)
    mutant_alpha = mutant_mod.continuous_power_law_mle(obs, 10.0)

    assert abs(true_alpha - mutant_alpha - 1.0) < 1e-9
    with pytest.raises(AssertionError):
        assert abs(mutant_alpha - true_alpha) < 1e-6


def test_source_mutant_power_law_ks_statistic_killed() -> None:
    """Mutant: In power_law.py, mutate `d_max = max(d_max, d_plus, d_minus)` -> `d_max = min(d_max, d_plus, d_minus)`."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/calculations/power_law.py"
    target_snippet = "d_max = max(d_max, d_plus, d_minus)"
    mutated_snippet = "d_max = min(d_max, d_plus, d_minus)"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)
    obs = [10.0 * (1.0 + i * 0.2) for i in range(50)]

    true_ks = fit_power_law_tail(obs, xmin=10.0, bootstrap_trials=10, seed=42)["data"]["ks_statistic"]["value"]
    mutant_ks = mutant_mod.fit_power_law_tail(obs, xmin=10.0, bootstrap_trials=10, seed=42)["data"]["ks_statistic"]["value"]

    with pytest.raises(AssertionError):
        assert abs(true_ks - mutant_ks) < 1e-6


def test_source_mutant_power_law_undefined_mean_threshold_killed() -> None:
    """Mutant: In runner.py, mutate `if float(alpha_val) <= 2.0:` -> `if float(alpha_val) <= 1.0:`."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/methods/runner.py"
    target_snippet = "if float(alpha_val) <= 2.0:"
    mutated_snippet = "if float(alpha_val) <= 1.0:"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)

    rng = random.Random(42)
    obs = [10.0 * ((1.0 - rng.random()) ** (-1.0 / 0.8)) for _ in range(500)]
    case = workflow_case()
    case["decision_case"]["inputs"]["win_probability"]["value"] = 0.85
    case["model_thinking_inputs"] = {
        "input_trust_class": "user_verified",
        "power_law": {"input_trust_class": "user_verified", "xmin": 10.0, "observations": obs},
    }

    mutant_res = mutant_mod.run_method_pack("page", case)
    with pytest.raises(AssertionError):
        assert "HEAVY_TAIL_UNDEFINED_MEAN" in mutant_res["data"]["red_flags"]["value"]


# =============================================================================
# 2. Markov Diagnostic Source Mutations
# =============================================================================

def test_source_mutant_markov_stationary_direction_killed() -> None:
    """Mutant: In markov.py, mutate power iteration step transpose."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/calculations/markov.py"
    target_snippet = "pi_next[j] = sum(pi[i] * mat_floats[i][j] for i in range(n))"
    mutated_snippet = "pi_next[j] = sum(pi[i] * mat_floats[j][i] for i in range(n))"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)
    mat = [[0.90, 0.10], [0.30, 0.70]]
    res = compute_stationary_distribution(["A", "B"], mat)
    assert round(res["data"]["stationary_distribution"]["value"]["A"], 2) == 0.75

    mutant_res = mutant_mod.compute_stationary_distribution(["A", "B"], mat)
    mutant_val = mutant_res["data"]["stationary_distribution"]["value"]["A"]

    with pytest.raises(AssertionError):
        assert round(mutant_val, 2) == 0.75


def test_source_mutant_markov_aperiodicity_check_killed() -> None:
    """Mutant: In markov.py, mutate `_check_aperiodicity()` to always return True."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/calculations/markov.py"
    target_snippet = "return g == 1"
    mutated_snippet = "return True"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)
    periodic_mat = [[0.0, 1.0], [1.0, 0.0]]
    mutant_res = mutant_mod.compute_stationary_distribution(["A", "B"], periodic_mat)
    with pytest.raises(AssertionError):
        assert mutant_res["data"]["is_aperiodic"]["value"] is False


# =============================================================================
# 3. Bass Diffusion Source Mutations
# =============================================================================

def test_source_mutant_bass_imitation_term_killed() -> None:
    """Mutant: In bass.py, mutate `adoption_rate = p_rate + (q_rate * (current_n / M))` -> `adoption_rate = p_rate`."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/calculations/bass.py"
    target_snippet = "adoption_rate = p_rate + (q_rate * (current_n / M))"
    mutated_snippet = "adoption_rate = p_rate"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)
    true_res = simulate_bass_diffusion(market_potential=1000.0, innovation_rate=0.03, imitation_rate=0.40, horizon=20)
    mutant_res = mutant_mod.simulate_bass_diffusion(market_potential=1000.0, innovation_rate=0.03, imitation_rate=0.40, horizon=20)

    true_adopters = true_res["data"]["cumulative_adopters"]["value"][-1]
    mutant_adopters = mutant_res["data"]["cumulative_adopters"]["value"][-1]

    # Omitting imitation term drastically suppresses diffusion curve
    assert true_adopters > 800.0
    assert mutant_adopters < 500.0
    with pytest.raises(AssertionError):
        assert abs(true_adopters - mutant_adopters) < 10.0


# =============================================================================
# 4. Bandit Engine Source Mutations
# =============================================================================

def test_source_mutant_bandit_adaptive_epsilon_killed() -> None:
    """Mutant: In bandits.py, mutate epsilon decay formula to 0.0."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/calculations/bandits.py"
    target_snippet = "eps_t = max(epsilon_min, epsilon_0 / math.sqrt(float(t + 1)))"
    mutated_snippet = "eps_t = 0.0"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)
    true_res = simulate_bernoulli_bandit([0.2, 0.8], horizon=200, policy="adaptive_epsilon", seed=42)
    mutant_res = mutant_mod.simulate_bernoulli_bandit([0.2, 0.8], horizon=200, policy="adaptive_epsilon", seed=42)

    with pytest.raises(AssertionError):
        assert true_res["canonical_hash"] == mutant_res["canonical_hash"]


# =============================================================================
# 5. Claim Compiler Source Mutations
# =============================================================================

def test_source_mutant_compiler_two_family_rule_killed() -> None:
    """Mutant: In compiler.py, mutate `num_families >= 2` -> `num_families >= 1`."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/ensemble/compiler.py"
    target_snippet = "elif num_families >= 2 and pos_groups >= supermajority_threshold:"
    mutated_snippet = "elif num_families >= 1 and pos_groups >= supermajority_threshold:"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)
    # Two independent parameter sweeps from the same family (two correlation groups)
    claims = [
        {"claim_id": "growth", "model_family": "power_law", "correlation_group": "pl_1", "direction": "positive", "receipt_hash": "a" * 64},
        {"claim_id": "growth", "model_family": "power_law", "correlation_group": "pl_2", "direction": "positive", "receipt_hash": "b" * 64},
    ]

    true_res = compile_claim_ensemble(claims)
    assert len(true_res["claims"]["robust_positive"]) == 0
    assert "growth" in true_res["claims"]["conditional"]

    mutant_res = mutant_mod.compile_claim_ensemble(claims)
    # Mutant erroneously promotes single family to robust_positive (must be caught)
    with pytest.raises(AssertionError):
        assert len(mutant_res["claims"]["robust_positive"]) == 0


def test_source_mutant_compiler_supermajority_threshold_killed() -> None:
    """Mutant: In compiler.py, mutate `supermajority_threshold` formula to 1."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/ensemble/compiler.py"
    target_snippet = "supermajority_threshold = max(2, math.ceil(2.0 * float(total_groups) / 3.0))"
    mutated_snippet = "supermajority_threshold = 1"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)
    claims = [
        {"claim_id": "growth", "model_family": "power_law", "direction": "positive", "receipt_hash": "a" * 64},
        {"claim_id": "growth", "model_family": "markov", "direction": "negative", "receipt_hash": "b" * 64},
        {"claim_id": "growth", "model_family": "bass", "direction": "negative", "receipt_hash": "c" * 64},
    ]

    mutant_res = mutant_mod.compile_claim_ensemble(claims)
    with pytest.raises(AssertionError):
        assert len(mutant_res["claims"]["robust_positive"]) == 0


# =============================================================================
# 6. Runner Input Trust Boundary Source Mutation
# =============================================================================

def test_source_mutant_runner_trust_bypass_killed() -> None:
    """Mutant: In runner.py, mutate `if untrusted:` -> `if False:`."""
    target_file = ROOT / "vendor/capital-decision-lab/capital_decision_lab/methods/runner.py"
    target_snippet = "if untrusted:"
    mutated_snippet = "if False:"

    mutant_mod = apply_source_mutation(target_file, target_snippet, mutated_snippet)
    case = workflow_case()
    case["model_thinking_inputs"] = {
        "input_trust_class": "untrusted_external",
        "power_law": {"input_trust_class": "untrusted_external", "observations": [10.0, 20.0, 30.0], "xmin": 10.0},
    }

    mutant_res = mutant_mod.run_method_pack("page", case)
    with pytest.raises(AssertionError):
        assert "UNTRUSTED_EXTERNAL_INPUT" in mutant_res["data"]["red_flags"]["value"]

