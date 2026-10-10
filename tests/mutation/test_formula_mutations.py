from __future__ import annotations

import math

import pytest

from capital_decision_lab.calculations import allocation, returns, risk, simulation


def test_sign_and_denominator_mutations_are_killed() -> None:
    assert returns.absolute_gain_loss(120.0, 100.0)["value"] == -20.0
    assert returns.roi(100.0, 120.0)["value"] == pytest.approx(0.2)


def test_annualization_mutation_is_killed() -> None:
    observations = [0.02, 0.04, 0.0]
    base = risk.sharpe(observations, baseline_rate=0.01, periods_per_year=1)["value"]
    annual = risk.sharpe(observations, baseline_rate=0.01, periods_per_year=4)["value"]
    assert annual == pytest.approx(base * 2.0)


def test_percentile_and_drawdown_direction_mutations_are_killed() -> None:
    modeled = simulation.monte_carlo(
        starting_value=100.0,
        mean_return=0.0,
        volatility=0.1,
        periods=1,
        iteration_count=300,
        seed=41,
    )["data"]
    assert modeled["terminal_p05"]["value"] < modeled["terminal_p95"]["value"]
    assert risk.maximum_drawdown([100.0, 120.0, 80.0])["value"] == pytest.approx(1.0 / 3.0)


def test_kelly_cap_and_seed_mutations_are_killed() -> None:
    assert allocation.capped_fractional_kelly(0.8, 2.0, 1.0, 0.1)["value"] == 0.1
    kwargs = dict(
        starting_value=100.0,
        mean_return=0.0,
        volatility=0.1,
        periods=2,
        iteration_count=100,
    )
    first = simulation.monte_carlo(**kwargs, seed=1)
    assert first == simulation.monte_carlo(**kwargs, seed=1)
    assert first != simulation.monte_carlo(**kwargs, seed=2)
