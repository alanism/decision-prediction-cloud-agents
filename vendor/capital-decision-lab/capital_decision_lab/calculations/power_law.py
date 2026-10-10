"""Continuous power-law tail diagnostic following Clauset et al. (2009)."""

from __future__ import annotations

import hashlib
import math
import random
from typing import Any

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import unavailable_result
from capital_decision_lab.evidence.common import atom

MIN_OBSERVATIONS = 50
MAX_OBSERVATIONS = 10_000
P_VALUE_THRESHOLD = 0.10


def _validate_observations(observations: Any, xmin: Any) -> str | None:
    if (
        not isinstance(xmin, (int, float))
        or isinstance(xmin, bool)
        or not math.isfinite(float(xmin))
        or float(xmin) <= 0
    ):
        return "xmin must be a positive finite number"

    if not isinstance(observations, list):
        return "observations must be a list"

    n = len(observations)
    if n < MIN_OBSERVATIONS or n > MAX_OBSERVATIONS:
        return f"observations count must be between {MIN_OBSERVATIONS} and {MAX_OBSERVATIONS}"

    xmin_f = float(xmin)
    sum_log = 0.0
    for x in observations:
        if (
            not isinstance(x, (int, float))
            or isinstance(x, bool)
            or not math.isfinite(float(x))
            or float(x) <= 0
        ):
            return "observations must be positive finite numbers"
        if float(x) < xmin_f:
            return "observations must be greater than or equal to xmin"
        sum_log += math.log(float(x) / xmin_f)

    if math.isclose(sum_log, 0.0, rel_tol=0.0, abs_tol=1e-12):
        return "observations must have positive variance above xmin"

    return None


def continuous_power_law_mle(observations: list[float], xmin: float) -> float:
    """Compute continuous maximum-likelihood estimate alpha = 1 + n / sum(ln(x / xmin))."""
    xmin_f = float(xmin)
    n = len(observations)
    sum_log = sum(math.log(float(x) / xmin_f) for x in observations)
    return 1.0 + float(n) / sum_log


def continuous_power_law_ks_distance(observations: list[float], xmin: float, alpha: float) -> float:
    """Compute Kolmogorov-Smirnov distance between continuous sample and power-law CDF."""
    xmin_f = float(xmin)
    gamma = float(alpha) - 1.0
    n = len(observations)
    sorted_obs = sorted(float(x) for x in observations)

    d_max = 0.0
    for i, x in enumerate(sorted_obs, start=1):
        # Theoretical CDF: F(x) = 1 - (x / xmin)^(-gamma)
        ratio = x / xmin_f
        cdf_theoretical = 1.0 - (ratio ** (-gamma))
        # Clamp to [0, 1] for numerical stability
        cdf_theoretical = max(0.0, min(1.0, cdf_theoretical))

        d_plus = (float(i) / float(n)) - cdf_theoretical
        d_minus = cdf_theoretical - (float(i - 1) / float(n))
        d_max = max(d_max, d_plus, d_minus)

    return d_max


def _derive_canonical_seed(observations: list[float], xmin: float, trials: int) -> int:
    hasher = hashlib.sha256()
    hasher.update(f"{xmin}:{trials}:".encode("utf-8"))
    for x in sorted(observations):
        hasher.update(f"{x:.10e},".encode("utf-8"))
    digest = hasher.hexdigest()
    return int(digest[:16], 16)


def _unavailable_model_result(reason: str, xmin: Any = None, observations_count: int = 0) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "contract_version": "nhi.model_result.v1",
        "result_id": "power_law_tail_unavailable",
        "model_id": "power_law_tail",
        "model_family": "power_law",
        "model_version": "1.0.0",
        "input_hash": "0" * 64,
        "data": {
            "alpha": unavailable_result(reason, unit="exponent"),
            "xmin": unavailable_result(reason, unit="threshold"),
            "mean_defined": unavailable_result(reason),
            "variance_defined": unavailable_result(reason),
            "ks_statistic": unavailable_result(reason, unit="distance"),
            "diagnostic_p_value": unavailable_result(reason, unit="p-value"),
            "power_law_not_rejected": unavailable_result(reason),
        },
        "metadata": {
            "algorithm_version": "clauset_mle_v1",
            "seed": "not_applicable",
            "bootstrap_trials": 0,
            "observations_count": observations_count,
        },
        "limitations": [
            "Diagnostic unavailable under supplied parameters or validation failure."
        ],
    }
    doc["canonical_hash"] = contract_payload_hash(doc)
    return doc


def fit_power_law_tail(
    observations: list[float],
    xmin: float,
    *,
    bootstrap_trials: int = 250,
    seed: int | str | None = None,
) -> dict[str, Any]:
    """Fit continuous power-law tail and evaluate goodness-of-fit diagnostic."""
    reason = _validate_observations(observations, xmin)
    if reason:
        return _unavailable_model_result(
            reason,
            xmin=xmin,
            observations_count=len(observations) if isinstance(observations, list) else 0,
        )

    xmin_f = float(xmin)
    obs_floats = [float(x) for x in observations]
    n = len(obs_floats)
    alpha = continuous_power_law_mle(obs_floats, xmin_f)
    ks_observed = continuous_power_law_ks_distance(obs_floats, xmin_f, alpha)

    # Parametric bootstrap
    actual_seed: int
    if seed is None or seed == "not_applicable":
        actual_seed = _derive_canonical_seed(obs_floats, xmin_f, bootstrap_trials)
    elif isinstance(seed, str):
        actual_seed = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16], 16)
    else:
        actual_seed = int(seed)

    rng = random.Random(actual_seed)
    gamma = alpha - 1.0
    count_exceeding = 0

    for _ in range(bootstrap_trials):
        # Generate synthetic power-law sample
        synth = [xmin_f * ((1.0 - rng.random()) ** (-1.0 / gamma)) for _ in range(n)]
        alpha_synth = continuous_power_law_mle(synth, xmin_f)
        ks_synth = continuous_power_law_ks_distance(synth, xmin_f, alpha_synth)
        if ks_synth > ks_observed:
            count_exceeding += 1

    p_value = float(count_exceeding) / float(bootstrap_trials)
    not_rejected = p_value >= P_VALUE_THRESHOLD

    mean_def = alpha > 2.0
    var_def = alpha > 3.0

    doc: dict[str, Any] = {
        "contract_version": "nhi.model_result.v1",
        "result_id": f"power_law_tail_res_{actual_seed % 1_000_000:06d}",
        "model_id": "power_law_tail",
        "model_family": "power_law",
        "model_version": "1.0.0",
        "input_hash": hashlib.sha256(
            f"{xmin_f}:{n}:{actual_seed}".encode("utf-8")
        ).hexdigest(),
        "data": {
            "alpha": atom(alpha, "calculated", unit="exponent", formula_ref="power_law.clauset_mle.v1"),
            "xmin": atom(xmin_f, "measured", unit="threshold"),
            "mean_defined": atom(mean_def, "calculated", formula_ref="power_law.moment.mean_defined.v1"),
            "variance_defined": atom(var_def, "calculated", formula_ref="power_law.moment.variance_defined.v1"),
            "ks_statistic": atom(ks_observed, "modeled", unit="distance", formula_ref="power_law.ks_distance.v1"),
            "diagnostic_p_value": atom(p_value, "modeled", unit="p-value", formula_ref="power_law.bootstrap_p_value.v1"),
            "power_law_not_rejected": atom(not_rejected, "modeled", formula_ref="power_law.diagnostic_gate.v1"),
        },
        "metadata": {
            "algorithm_version": "clauset_mle_v1",
            "seed": actual_seed,
            "bootstrap_trials": bootstrap_trials,
            "observations_count": n,
        },
        "limitations": [
            "Goodness-of-fit diagnostic tests plausibility against continuous power law; not rejected does not constitute proof of power-law generation."
        ],
    }
    doc["canonical_hash"] = contract_payload_hash(doc)
    return doc


def analyze_power_law_input(model_input: dict) -> dict[str, Any]:
    """Execute power-law tail diagnostic over an nhi.model_input.v1 envelope."""
    trust_class = model_input.get("input_trust_class")
    if trust_class == "untrusted_external":
        return _unavailable_model_result("untrusted input requires user confirmation")

    params = model_input.get("parameters", {})
    xmin = params.get("xmin")
    observations = params.get("observations")
    seed = model_input.get("metadata", {}).get("seed")

    return fit_power_law_tail(observations, xmin, seed=seed)
