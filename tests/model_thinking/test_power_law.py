from __future__ import annotations

import math
import random
from pathlib import Path

from capital_decision_lab.calculations.power_law import (
    continuous_power_law_ks_distance,
    continuous_power_law_mle,
    fit_power_law_tail,
)
from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import validate_contract

ROOT = Path(__file__).resolve().parents[2]


def generate_synthetic_power_law(alpha: float, xmin: float, n: int, seed: int = 42) -> list[float]:
    """Generate n samples from continuous power law with PDF p(x) ~ x^-alpha for x >= xmin."""
    rng = random.Random(seed)
    gamma = alpha - 1.0
    return [xmin * ((1.0 - rng.random()) ** (-1.0 / gamma)) for _ in range(n)]


def test_continuous_power_law_mle_formula() -> None:
    xmin = 10.0
    # Direct analytical test: if x = [10*e^1, 10*e^2], n=2, sum(ln(x/xmin)) = 3 -> alpha = 1 + 2/3 = 1.6666666667
    obs = [10.0 * math.e, 10.0 * (math.e**2)]
    alpha = continuous_power_law_mle(obs, xmin)
    assert math.isclose(alpha, 1.0 + 2.0 / 3.0, rel_tol=0.0, abs_tol=1e-10)


def test_continuous_power_law_mle_synthetic_recovery() -> None:
    true_alpha = 2.5
    xmin = 10.0
    obs = generate_synthetic_power_law(true_alpha, xmin, 2000, seed=12345)
    estimated_alpha = continuous_power_law_mle(obs, xmin)
    assert math.isclose(estimated_alpha, true_alpha, rel_tol=0.05, abs_tol=0.1)


def test_continuous_power_law_ks_distance() -> None:
    xmin = 10.0
    alpha = 2.5
    obs = generate_synthetic_power_law(alpha, xmin, 500, seed=42)
    ks_stat = continuous_power_law_ks_distance(obs, xmin, alpha)
    assert 0.0 <= ks_stat <= 1.0
    assert ks_stat < 0.10  # For true power law, KS distance is small


def test_power_law_moment_definitions() -> None:
    xmin = 10.0
    # Case 1: alpha = 1.8 (undefined mean, undefined variance)
    obs_heavy = generate_synthetic_power_law(1.8, xmin, 200, seed=101)
    res_heavy = fit_power_law_tail(obs_heavy, xmin, bootstrap_trials=50, seed=42)
    assert res_heavy["data"]["mean_defined"]["value"] is False
    assert res_heavy["data"]["variance_defined"]["value"] is False

    # Case 2: alpha = 2.5 (defined mean, undefined variance)
    obs_med = generate_synthetic_power_law(2.5, xmin, 200, seed=102)
    res_med = fit_power_law_tail(obs_med, xmin, bootstrap_trials=50, seed=42)
    assert res_med["data"]["mean_defined"]["value"] is True
    assert res_med["data"]["variance_defined"]["value"] is False

    # Case 3: alpha = 3.5 (defined mean, defined variance)
    obs_light = generate_synthetic_power_law(3.5, xmin, 200, seed=103)
    res_light = fit_power_law_tail(obs_light, xmin, bootstrap_trials=50, seed=42)
    assert res_light["data"]["mean_defined"]["value"] is True
    assert res_light["data"]["variance_defined"]["value"] is True


def test_power_law_diagnostic_result_contract() -> None:
    xmin = 10.0
    obs = generate_synthetic_power_law(2.4, xmin, 100, seed=999)
    result = fit_power_law_tail(obs, xmin, bootstrap_trials=250, seed=42)

    assert result["contract_version"] == "nhi.model_result.v1"
    assert result["model_family"] == "power_law"
    assert result["model_id"] == "power_law_tail"
    assert "alpha" in result["data"]
    assert "xmin" in result["data"]
    assert "diagnostic_p_value" in result["data"]
    assert "power_law_not_rejected" in result["data"]

    # Provenance checking
    assert result["data"]["alpha"]["provenance_class"] == "calculated"
    assert result["data"]["diagnostic_p_value"]["provenance_class"] == "modeled"

    # Schema validation
    issues = validate_contract(result)
    assert not issues, f"Contract validation failed: {issues}"

    # Verify no claim of "proven" in limitations or results
    for lim in result["limitations"]:
        assert "proven" not in lim.lower()
    for atom_val in result["data"].values():
        if "reason" in atom_val and atom_val["reason"]:
            assert "proven" not in atom_val["reason"].lower()
