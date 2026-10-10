from __future__ import annotations

from capital_decision_lab.calculations import simulation
from capital_decision_lab.contracts.validation import validate_evidence_atom


def test_bull_base_bear_scenario_analysis() -> None:
    scenarios = {
        "bull": {"probability": 0.25, "return": 0.3},
        "base": {"probability": 0.5, "return": 0.1},
        "bear": {"probability": 0.25, "return": -0.2},
    }
    result = simulation.scenario_analysis(scenarios)
    assert set(result["data"]) == {"scenario_bull", "scenario_base", "scenario_bear", "scenario_expected_return"}
    assert result["data"]["scenario_expected_return"]["value"] == 0.075
    assert all(validate_evidence_atom(atom) == [] for atom in result["data"].values())


def test_seeded_monte_carlo_is_repeatable_and_records_metadata() -> None:
    kwargs = {
        "starting_value": 1000.0,
        "mean_return": 0.01,
        "volatility": 0.02,
        "periods": 12,
        "iteration_count": 500,
        "seed": 73021,
    }
    first = simulation.monte_carlo(**kwargs)
    second = simulation.monte_carlo(**kwargs)
    assert first == second
    assert first["metadata"]["seed"] == 73021
    assert first["metadata"]["distribution_family"] == "normal"
    assert first["metadata"]["iteration_count"] == 500
    assert first["metadata"]["parameters"]["periods"] == 12
    assert len(first["metadata"]["input_hashes"]) == 1
    assert first["metadata"]["limitations"]
    assert all(validate_evidence_atom(atom) == [] for atom in first["data"].values())


def test_seed_changes_modeled_output() -> None:
    common = dict(
        starting_value=1000.0,
        mean_return=0.01,
        volatility=0.02,
        periods=12,
        iteration_count=200,
    )
    assert simulation.monte_carlo(**common, seed=1)["data"] != simulation.monte_carlo(**common, seed=2)["data"]


def test_percentiles_are_ordered() -> None:
    data = simulation.monte_carlo(
        starting_value=1000.0,
        mean_return=0.0,
        volatility=0.1,
        periods=1,
        iteration_count=500,
        seed=9,
    )["data"]
    assert data["terminal_p05"]["value"] <= data["terminal_p50"]["value"] <= data["terminal_p95"]["value"]


def test_invalid_simulation_and_scenario_inputs_are_unavailable() -> None:
    invalid_simulation = simulation.monte_carlo(
        starting_value=0.0,
        mean_return=0.0,
        volatility=-0.1,
        periods=0,
        iteration_count=0,
        seed=1,
    )
    assert invalid_simulation["data"]["simulation_result"]["provenance_class"] == "unavailable"

    invalid_scenarios = simulation.scenario_analysis(
        {
            "bull": {"probability": 0.5, "return": 0.3},
            "base": {"probability": 0.5, "return": 0.1},
            "bear": {"probability": 0.5, "return": -0.2},
        }
    )
    assert invalid_scenarios["data"]["scenario_result"]["provenance_class"] == "unavailable"
