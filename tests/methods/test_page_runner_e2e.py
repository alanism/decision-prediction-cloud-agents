"""End-to-end integration and boundary tests for the Page Method Pack runner."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from capital_decision_lab.methods.runner import run_method_pack
from tests.orchestration.test_analyze_position import workflow_case


def test_page_runner_executes_all_four_models() -> None:
    """Test that Page runner executes power_law, markov, bass, and bandits when present."""
    case = workflow_case()
    case["model_thinking_inputs"] = {
        "trust_class": "user_verified",
        "power_law": {
            "observations": [10.0 * (1.0 + i * 0.1) for i in range(100)],
            "xmin": 10.0,
        },
        "markov": {
            "states": ["bear", "bull"],
            "transition_matrix": [[0.8, 0.2], [0.3, 0.7]],
        },
        "bass": {
            "M": 10000.0,
            "p": 0.03,
            "q": 0.38,
            "horizon": 20,
        },
        "bandit": {
            "arm_probabilities": [0.3, 0.7],
            "horizon": 50,
            "policy": "adaptive_epsilon",
        },
    }

    result = run_method_pack("page", case)
    assert result["contract_version"] == "nhi.method_pack_result.v1"
    calcs = result["data"]["method_specific_calculations"]["value"]

    # Assert all four model results are computed and stored
    assert "power_law_result" in calcs
    assert "markov_result" in calcs
    assert "bass_result" in calcs
    assert "bandit_result" in calcs

    # Assert claim ensemble compiler was executed and produced an ensemble_result
    assert "ensemble_result" in calcs
    assert calcs["ensemble_result"] is not None
    assert calcs["ensemble_result"]["contract_version"] == "nhi.ensemble_result.v1"


def test_page_runner_rejects_untrusted_external_inputs() -> None:
    """Test that Page runner rejects model inputs with trust_class 'untrusted_external'."""
    case = workflow_case()
    case["model_thinking_inputs"] = {
        "trust_class": "untrusted_external",
        "power_law": {
            "observations": [10.0 * (1.0 + i * 0.1) for i in range(100)],
            "xmin": 10.0,
        },
        "markov": {
            "states": ["bear", "bull"],
            "transition_matrix": [[0.8, 0.2], [0.3, 0.7]],
        },
    }

    result = run_method_pack("page", case)
    flags = result["data"]["red_flags"]["value"]
    rec = result["data"]["model_implied_recommendation"]["value"]

    assert "UNTRUSTED_EXTERNAL_INPUT" in flags
    assert rec in {"pause", "watch"}
    calcs = result["data"]["method_specific_calculations"]["value"]
    assert calcs.get("trust_status") == "rejected"


def test_page_runner_compiler_two_family_minimum() -> None:
    """Test that single-family support does not yield robust_positive recommendation."""
    case = workflow_case()
    # Observations with alpha ~ 4.3 (> 3.0, finite mean and variance)
    obs = [10.0 * ((1.0 - (i + 0.5) / 200.0) ** (-0.3)) for i in range(200)]
    case["model_thinking_inputs"] = {
        "trust_class": "user_verified",
        "power_law": {
            "observations": obs,
            "xmin": 10.0,
        },
    }

    result = run_method_pack("page", case)
    calcs = result["data"]["method_specific_calculations"]["value"]
    ensemble = calcs.get("ensemble_result")
    assert ensemble is not None
    assert ensemble["applicable_family_count"] == 1
    assert len(ensemble["claims"]["robust_positive"]) == 0
    assert "thesis_upside" in ensemble["claims"]["conditional"]


def test_page_runner_supermajority_two_families_positive() -> None:
    """Test that two distinct model families agreeing on positive yield positive recommendation."""
    case = workflow_case()
    case["decision_case"]["inputs"]["win_probability"]["value"] = 0.85
    obs = [10.0 * ((1.0 - (i + 0.5) / 200.0) ** (-0.3)) for i in range(200)]
    case["model_thinking_inputs"] = {
        "trust_class": "user_verified",
        "power_law": {
            "observations": obs,
            "xmin": 10.0,
        },
        "bass": {
            "M": 10000.0,
            "p": 0.05,
            "q": 0.40,
            "horizon": 20,
        },
    }

    result = run_method_pack("page", case)
    rec = result["data"]["model_implied_recommendation"]["value"]
    assert rec in {"increase exposure", "increase exposure under this assumption set"}
    assert result["data"]["target_exposure"]["value"] > 0.0


def test_page_runner_heavy_tail_veto_suppresses_multi_model() -> None:
    """Test that an active heavy-tail moment veto suppresses positive multi-model support."""
    case = workflow_case()
    case["decision_case"]["inputs"]["win_probability"]["value"] = 0.85

    # Power law with alpha <= 2.0 (undefined mean)
    rng = random.Random(42)
    obs = [10.0 * ((1.0 - rng.random()) ** (-1.0 / 0.8)) for _ in range(500)]

    case["model_thinking_inputs"] = {
        "trust_class": "user_verified",
        "power_law": {
            "observations": obs,
            "xmin": 10.0,
        },
        "bass": {
            "M": 10000.0,
            "p": 0.05,
            "q": 0.40,
            "horizon": 20,
        },
    }

    result = run_method_pack("page", case)
    rec = result["data"]["model_implied_recommendation"]["value"]
    flags = result["data"]["red_flags"]["value"]
    assert "HEAVY_TAIL_UNDEFINED_MEAN" in flags
    assert rec == "watch"


@pytest.mark.parametrize("invalid_inputs", [
    [],
    [{"model_family": "power_law"}],
    "string_not_dict",
    12345,
    True,
    False,
])
def test_page_runner_handles_non_dict_model_inputs_safely(invalid_inputs) -> None:
    """Test that Page runner returns deterministic pause result without exception on non-dict inputs."""
    case = workflow_case()
    case["model_thinking_inputs"] = invalid_inputs

    result = run_method_pack("page", case)
    assert result["contract_version"] == "nhi.method_pack_result.v1"
    assert result["data"]["model_implied_recommendation"]["value"] == "pause"
    assert "SCHEMA_INVALID_MODEL_INPUTS" in result["data"]["red_flags"]["value"]
    calcs = result["data"]["method_specific_calculations"]["value"]
    assert calcs["trust_status"] == "rejected"
    assert "SCHEMA_INVALID_MODEL_INPUTS" in calcs["binding_vetoes"]


def test_page_runner_handles_non_dict_model_entry_safely() -> None:
    """Test that Page runner safely handles a model entry that is not a dict."""
    case = workflow_case()
    case["model_thinking_inputs"] = {
        "trust_class": "user_verified",
        "power_law": "not_a_dict_entry",
    }

    result = run_method_pack("page", case)
    assert result["contract_version"] == "nhi.method_pack_result.v1"
    assert result["data"]["model_implied_recommendation"]["value"] == "pause"
    assert "SCHEMA_INVALID_MODEL_INPUTS" in result["data"]["red_flags"]["value"]
    calcs = result["data"]["method_specific_calculations"]["value"]
    assert calcs["trust_status"] == "rejected"


def test_page_runner_handles_contract_schema_invalid_entry_safely() -> None:
    """Test that Page runner safely rejects a contract_version declared model input with schema errors."""
    case = workflow_case()
    case["model_thinking_inputs"] = {
        "trust_class": "user_verified",
        "power_law": {
            "contract_version": "nhi.model_input.v1",
            "model_id": "pl_1",
            "model_family": "unsupported_family_name",  # Schema enum mismatch
            "model_version": "v1.0",
            "input_trust_class": "user_verified",
            "parameters": {},
        },
    }

    result = run_method_pack("page", case)
    assert result["contract_version"] == "nhi.method_pack_result.v1"
    assert result["data"]["model_implied_recommendation"]["value"] == "pause"
    assert "SCHEMA_INVALID_MODEL_INPUTS" in result["data"]["red_flags"]["value"]


def test_page_runner_handles_malformed_parameters_without_crashing() -> None:
    """Test that Page runner handles malformed internal numerical parameters gracefully."""
    case = workflow_case()
    case["model_thinking_inputs"] = {
        "trust_class": "user_verified",
        "power_law": {
            "observations": "not_a_list",
            "xmin": "not_a_number",
        },
        "markov": {
            "states": "not_a_list",
            "transition_matrix": "not_a_matrix",
        },
    }

    result = run_method_pack("page", case)
    assert result["contract_version"] == "nhi.method_pack_result.v1"
    # Returns safe watch/pause without crashing
    assert result["data"]["model_implied_recommendation"]["value"] in {"watch", "pause"}


