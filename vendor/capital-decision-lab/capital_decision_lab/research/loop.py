"""Deterministic missing-input mini-loops for guided research."""

from __future__ import annotations


_KELLY = {"win_probability", "upside_payoff", "downside_loss", "capital_at_risk", "max_exposure_cap"}
_MARGIN = {"maintenance_margin_requirement", "borrowed_amount", "current_price", "shares"}


def _value_map(case: dict) -> dict:
    result = {}
    for name, value in case.get("inputs", {}).items():
        result[name] = value.get("value") if isinstance(value, dict) and "value" in value else value
    return result


def evaluate_research_readiness(case: dict, *, evidence: dict | None = None) -> dict:
    values = _value_map(case)
    requests = []
    missing_kelly = sorted(name for name in _KELLY if values.get(name) is None)
    missing_margin = sorted(name for name in _MARGIN if values.get(name) is None)
    if missing_kelly:
        requests.append({"code": "KELLY_INPUTS_REQUIRED", "missing": missing_kelly, "prompt": "Kelly analysis needs probability, payoff, capital at risk, and an exposure cap."})
    if missing_margin:
        requests.append({"code": "MARGIN_INPUTS_REQUIRED", "missing": missing_margin, "prompt": "Margin analysis needs the maintenance requirement, borrowing, price, and shares."})
    if evidence is not None:
        status = evidence.get("verification_status")
        if status not in {"auto_retrieved", "user_verified", "user_corrected"}:
            return {"status": "blocked_low_confidence", "requests": [{"code": "EVIDENCE_VERIFICATION_REQUIRED", "prompt": "Confirm extracted evidence before a belief update."}]}
        contradiction = evidence.get("data", {}).get("contradiction_score", {}).get("value", 0.0)
        if contradiction >= 0.7:
            return {"status": "blocked_missing_user_input", "requests": [{"code": "EVIDENCE_CONTRADICTION_REQUIRES_WEIGHT", "prompt": "Evidence channels conflict. Choose which thesis channel carries more weight."}]}
    return {"status": "blocked_missing_user_input" if requests else "analysis_ready", "requests": requests}
