"""Seeded scenario and Monte Carlo modeled ranges."""

from __future__ import annotations

import math
import random
import statistics
from typing import Any

from capital_decision_lab.contracts.canonical import canonical_sha256
from capital_decision_lab.contracts.validation import unavailable_result


_LIMITATIONS = [
    "Modeled range from supplied parameters, not a prediction",
    "Normal draws are bounded at a total loss for each period",
]


def _modeled(value: Any, *, unit: str, formula_ref: str, refs: list[str], limitations: list[str] | None = None) -> dict:
    return {
        "value": value,
        "provenance_class": "modeled",
        "unit": unit,
        "input_refs": refs,
        "formula_ref": formula_ref,
        "limitations": limitations or list(_LIMITATIONS),
    }


def scenario_analysis(scenarios: dict) -> dict:
    required = {"bull", "base", "bear"}
    valid = isinstance(scenarios, dict) and set(scenarios) == required
    if valid:
        for item in scenarios.values():
            valid = (
                isinstance(item, dict)
                and isinstance(item.get("probability"), (int, float))
                and not isinstance(item.get("probability"), bool)
                and isinstance(item.get("return"), (int, float))
                and not isinstance(item.get("return"), bool)
                and 0 <= item["probability"] <= 1
                and math.isfinite(float(item["probability"]))
                and math.isfinite(float(item["return"]))
            )
            if not valid:
                break
    if valid:
        valid = math.isclose(
            sum(float(item["probability"]) for item in scenarios.values()),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    if not valid:
        return {
            "data": {
                "scenario_result": unavailable_result(
                    "bull, base, and bear probabilities must be valid and sum to one",
                    unit="ratio",
                    input_refs=["scenarios"],
                )
            },
            "metadata": {"distribution_family": "discrete scenarios"},
        }
    data = {
        f"scenario_{name}": _modeled(
            float(item["return"]),
            unit="ratio",
            formula_ref="simulation.scenario.v1",
            refs=[f"scenarios.{name}"],
            limitations=["Scenario value supplied by the user"],
        )
        for name, item in scenarios.items()
    }
    expected = sum(
        float(item["probability"]) * float(item["return"])
        for item in scenarios.values()
    )
    data["scenario_expected_return"] = _modeled(
        expected,
        unit="ratio",
        formula_ref="simulation.scenario_expected_return.v1",
        refs=["scenarios"],
        limitations=["Weighted only by supplied scenario probabilities"],
    )
    return {
        "data": data,
        "metadata": {
            "distribution_family": "discrete scenarios",
            "parameters": scenarios,
            "input_hashes": [canonical_sha256(scenarios)],
            "limitations": ["Scenario values and probabilities are supplied inputs"],
        },
    }


def _percentile(sorted_values: list[float], probability: float) -> float:
    index = int(math.floor((len(sorted_values) - 1) * probability))
    return sorted_values[index]


def monte_carlo(
    *,
    starting_value: float,
    mean_return: float,
    volatility: float,
    periods: int,
    iteration_count: int,
    seed: int,
    distribution_family: str = "normal",
) -> dict:
    parameters = {
        "starting_value": starting_value,
        "mean_return": mean_return,
        "volatility": volatility,
        "periods": periods,
    }
    metadata = {
        "seed": seed,
        "distribution_family": distribution_family,
        "parameters": parameters,
        "iteration_count": iteration_count,
        "input_hashes": [canonical_sha256(parameters)],
        "limitations": list(_LIMITATIONS),
    }
    numeric = all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        for value in (starting_value, mean_return, volatility)
    )
    valid = (
        numeric
        and starting_value > 0
        and volatility >= 0
        and isinstance(periods, int)
        and not isinstance(periods, bool)
        and periods > 0
        and isinstance(iteration_count, int)
        and not isinstance(iteration_count, bool)
        and 0 < iteration_count <= 1_000_000
        and isinstance(seed, int)
        and not isinstance(seed, bool)
        and distribution_family == "normal"
    )
    if not valid:
        return {
            "data": {
                "simulation_result": unavailable_result(
                    "simulation parameters are outside the supported domain",
                    unit="currency",
                    input_refs=["simulation"],
                    limitations=list(_LIMITATIONS),
                )
            },
            "metadata": metadata,
        }

    generator = random.Random(seed)
    terminal_values: list[float] = []
    for _ in range(iteration_count):
        terminal = float(starting_value)
        for _ in range(periods):
            period_return = max(generator.gauss(float(mean_return), float(volatility)), -1.0)
            terminal *= 1.0 + period_return
        terminal_values.append(terminal)
    ordered = sorted(terminal_values)
    refs = ["simulation"]
    data = {
        "terminal_p05": _modeled(_percentile(ordered, 0.05), unit="currency", formula_ref="simulation.monte_carlo.p05.v1", refs=refs),
        "terminal_p50": _modeled(_percentile(ordered, 0.50), unit="currency", formula_ref="simulation.monte_carlo.p50.v1", refs=refs),
        "terminal_p95": _modeled(_percentile(ordered, 0.95), unit="currency", formula_ref="simulation.monte_carlo.p95.v1", refs=refs),
        "terminal_mean": _modeled(statistics.fmean(terminal_values), unit="currency", formula_ref="simulation.monte_carlo.mean.v1", refs=refs),
        "simulation_loss_probability": _modeled(
            sum(value < starting_value for value in terminal_values) / iteration_count,
            unit="probability",
            formula_ref="simulation.monte_carlo.loss_probability.v1",
            refs=refs,
        ),
    }
    return {"data": data, "metadata": metadata}
