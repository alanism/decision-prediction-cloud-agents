"""Bass diffusion discrete dynamical model."""

from __future__ import annotations

import hashlib
import math
from typing import Any

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.contracts.validation import unavailable_result
from capital_decision_lab.evidence.common import atom

MAX_MARKET_POTENTIAL = 1e9
MIN_HORIZON = 1
MAX_HORIZON = 10_000


def _unavailable_bass_result(reason: str) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "contract_version": "nhi.model_result.v1",
        "result_id": "bass_diffusion_unavailable",
        "model_id": "bass_diffusion",
        "model_family": "bass",
        "model_version": "1.0.0",
        "input_hash": "0" * 64,
        "data": {
            "cumulative_adopters": unavailable_result(reason, unit="adopters"),
            "new_adopters": unavailable_result(reason, unit="adopters/period"),
            "peak_adoption_period": unavailable_result(reason, unit="period_index"),
            "peak_adoption_rate": unavailable_result(reason, unit="adopters/period"),
            "market_penetration_pct": unavailable_result(reason, unit="percent"),
        },
        "metadata": {
            "algorithm_version": "discrete_bass_v1",
            "seed": "not_applicable",
            "horizon": 0,
            "market_potential": 0.0,
        },
        "limitations": [
            "Bass diffusion dynamics unavailable under supplied parameters or boundary violation."
        ],
    }
    doc["canonical_hash"] = contract_payload_hash(doc)
    return doc


def simulate_bass_diffusion(
    market_potential: float,
    innovation_rate: float,
    imitation_rate: float,
    *,
    initial_adopters: float = 0.0,
    horizon: int = 20,
) -> dict[str, Any]:
    """Execute discrete Bass diffusion simulation over finite horizon."""
    # Type and finiteness validation
    params = [market_potential, innovation_rate, imitation_rate, initial_adopters, horizon]
    for p in params:
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(float(p)):
            return _unavailable_bass_result("parameters must be finite numbers")

    M = float(market_potential)
    p_rate = float(innovation_rate)
    q_rate = float(imitation_rate)
    N0 = float(initial_adopters)
    T = int(horizon)

    if M <= 0.0 or M > MAX_MARKET_POTENTIAL:
        return _unavailable_bass_result(f"market potential must be positive and at most 1e9")

    if p_rate < 0.0 or q_rate < 0.0:
        return _unavailable_bass_result("innovation and imitation rates must be non-negative")

    if p_rate + q_rate > 1.0:
        return _unavailable_bass_result("sum of innovation and imitation rates must not exceed 1.0")

    if N0 < 0.0 or N0 > M:
        return _unavailable_bass_result("initial adopters must be between 0 and market potential")

    if p_rate == 0.0 and N0 == 0.0:
        return _unavailable_bass_result("positive adoption requires either positive innovation rate or non-zero initial adopters")

    if T < MIN_HORIZON or T > MAX_HORIZON:
        return _unavailable_bass_result(f"horizon must be between {MIN_HORIZON} and {MAX_HORIZON} periods")

    # Simulation loop
    cum: list[float] = [N0]
    new_ad: list[float] = []

    current_n = N0
    for t in range(T):
        remaining = max(0.0, M - current_n)
        adoption_rate = p_rate + (q_rate * (current_n / M))
        delta_n = min(remaining, max(0.0, adoption_rate * remaining))
        next_n = min(M, current_n + delta_n)

        new_ad.append(delta_n)
        cum.append(next_n)
        current_n = next_n

    peak_period = 0
    max_rate = -1.0
    for idx, rate in enumerate(new_ad):
        if rate > max_rate:
            max_rate = rate
            peak_period = idx

    penetration_pct = (current_n / M) * 100.0

    input_hash = hashlib.sha256(f"{M:.8e}:{p_rate:.8e}:{q_rate:.8e}:{N0:.8e}:{T}".encode("utf-8")).hexdigest()

    doc: dict[str, Any] = {
        "contract_version": "nhi.model_result.v1",
        "result_id": f"bass_res_{input_hash[:16]}",
        "model_id": "bass_diffusion",
        "model_family": "bass",
        "model_version": "1.0.0",
        "input_hash": input_hash,
        "data": {
            "cumulative_adopters": atom(cum, "calculated", formula_ref="bass.discrete_cumulative.v1", unit="adopters"),
            "new_adopters": atom(new_ad, "calculated", formula_ref="bass.discrete_increments.v1", unit="adopters/period"),
            "peak_adoption_period": atom(peak_period, "calculated", unit="period_index"),
            "peak_adoption_rate": atom(max_rate, "calculated", unit="adopters/period"),
            "market_penetration_pct": atom(penetration_pct, "calculated", unit="percent"),
        },
        "metadata": {
            "algorithm_version": "discrete_bass_v1",
            "seed": "not_applicable",
            "horizon": T,
            "market_potential": M,
            "innovation_rate": p_rate,
            "imitation_rate": q_rate,
            "initial_adopters": N0,
        },
        "limitations": [
            "Discrete Bass diffusion assumes fixed total market potential and stationary innovation/imitation coefficients."
        ],
    }
    doc["canonical_hash"] = contract_payload_hash(doc)
    return doc


def analyze_bass_input(model_input: dict) -> dict[str, Any]:
    """Execute Bass diffusion simulation over an nhi.model_input.v1 envelope."""
    trust_class = model_input.get("input_trust_class")
    if trust_class == "untrusted_external":
        return _unavailable_bass_result("untrusted input requires user confirmation")

    params = model_input.get("parameters", {})
    market_potential = params.get("market_potential")
    innovation_rate = params.get("innovation_rate")
    imitation_rate = params.get("imitation_rate")
    initial_adopters = params.get("initial_adopters", 0.0)
    horizon = params.get("horizon", 20)

    return simulate_bass_diffusion(
        market_potential,
        innovation_rate,
        imitation_rate,
        initial_adopters=initial_adopters,
        horizon=horizon,
    )
