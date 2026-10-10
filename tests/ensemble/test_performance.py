from __future__ import annotations

import time
from pathlib import Path

from capital_decision_lab.ensemble.compiler import compile_claim_ensemble

ROOT = Path(__file__).resolve().parents[2]


def test_ensemble_compiler_performance_budget_1000_claims() -> None:
    # 1,000 synthetic model claim receipts across 4 families and 10 claims
    families = ["power_law", "markov", "bass", "bandit"]
    claims = []
    for i in range(1000):
        family = families[i % 4]
        claim_id = f"claim_{i % 10}"
        direction = "positive" if (i % 3 != 0) else "negative"
        h = f"{i:04x}" * 16
        claims.append(
            {
                "claim_id": claim_id,
                "model_family": family,
                "model_id": f"{family}_{i}",
                "direction": direction,
                "receipt_hash": h,
                "correlation_group": f"group_{i % 5}",
            }
        )

    start = time.perf_counter()
    res = compile_claim_ensemble(claims)
    elapsed = time.perf_counter() - start

    assert res["contract_version"] == "nhi.ensemble_result.v1"
    # Strict performance requirement: compiling 1,000 claim receipts must complete in < 5.0 seconds
    assert elapsed < 5.0, f"Compilation took {elapsed:.3f}s exceeding 5.0s budget"
