"""Run method packs as deterministic overlays on the shared analysis substrate."""

from __future__ import annotations

from capital_decision_lab.contracts.canonical import canonical_sha256, contract_payload_hash
from capital_decision_lab.evidence.common import atom
from capital_decision_lab.orchestration.analyze import analyze_case

from .packs import PACKS


def available_method_packs() -> list[str]:
    return sorted(PACKS)


def _value(analysis: dict, name: str, default=0.0):
    value = analysis.get("data", {}).get(name, {}).get("value")
    return default if value is None else value


def run_method_pack(pack_id: str, case_bundle: dict, *, base_result: dict | None = None) -> dict:
    if pack_id not in PACKS or pack_id == "committee":
        raise ValueError("METHOD_PACK_UNKNOWN")
    case = case_bundle.get("decision_case", case_bundle)
    analysis = (base_result or {}).get("analysis") or analyze_case(case)
    portfolio = case_bundle.get("portfolio")
    thesis = case_bundle.get("thesis")
    missing = [name for name, value in (("portfolio", portfolio), ("thesis", thesis)) if not value]
    flags: list[str] = []
    modifiers = list(PACKS[pack_id]["recommendation_modifiers"])
    evidence_used: list[str] = []
    current = float((portfolio or {}).get("positions", [{}])[0].get("position_weight", 0.0))
    recommendation = "hold current exposure"
    confidence = float(case_bundle.get("method_inputs", {}).get("evidence_quality", 0.5))
    target = current
    calculations = {"shared_analysis_hash": analysis["canonical_hash"]}

    if pack_id == "thorp":
        full = float(_value(analysis, "full_kelly_fraction"))
        fraction = 0.25 if confidence < 0.4 else 0.5
        target = max(0.0, min(float(_value(analysis, "capped_exposure", full)), full * fraction))
        rows = _value(analysis, "margin_stress_table", []) or []
        margin_danger = float(_value(analysis, "liquidation_buffer_percent", 0.0)) <= 0 or any(row.get("maintenance_breach") for row in rows)
        if margin_danger:
            recommendation = "avoid margin"; flags.append("MARGIN_SURVIVAL_BINDING")
        elif target < current:
            recommendation = "trim to fractional Kelly"
        elif target > current:
            recommendation = "increase exposure under this assumption set"
        calculations.update({"full_kelly": full, "kelly_fraction_applied": fraction, "max_leverage": float(case_bundle.get("method_inputs", {}).get("max_leverage", 2.0))})
    elif pack_id == "mauboussin":
        probabilities = (thesis or {}).get("probabilities")
        if not isinstance(probabilities, dict) or any(not isinstance(value, (int, float)) for value in probabilities.values()):
            flags.append("NUMERICAL_PROBABILITIES_REQUIRED"); missing.append("numerical_probabilities"); recommendation = "pause"
        base_rate = case_bundle.get("method_inputs", {}).get("base_rate")
        user_probability = probabilities.get("bull") if isinstance(probabilities, dict) else None
        if isinstance(base_rate, (int, float)) and isinstance(user_probability, (int, float)) and user_probability - base_rate >= 0.15:
            flags.append("BASE_RATE_OVERCONFIDENCE"); recommendation = "watch"
        calculations.update({"base_rate": base_rate, "user_bull_probability": user_probability})
    elif pack_id == "contrarian_filings":
        filings = [item for item in case_bundle.get("filing_evidence", []) if item.get("source_type") == "filings" and item.get("verification_status") in {"auto_retrieved", "user_verified", "user_corrected"}]
        if not filings:
            flags.append("PRIMARY_FILINGS_REQUIRED"); missing.append("primary_filings"); recommendation = "watch"
        else:
            evidence_used.append("filings")
        calculations["verified_filing_count"] = len(filings)
    elif pack_id == "page":
        raw_inputs = case_bundle.get("model_thinking_inputs")
        claims: list[dict] = []
        vetoes: list[str] = []

        # Validate envelope structure
        if not isinstance(raw_inputs, dict):
            flags.append("SCHEMA_INVALID_MODEL_INPUTS")
            flags.append("MALFORMED_MODEL_INPUTS")
            missing.append("model_thinking_inputs")
            recommendation = "pause"
            calculations["trust_status"] = "rejected"
            calculations["binding_vetoes"] = ["SCHEMA_INVALID_MODEL_INPUTS"]
            calculations["compiled_claims"] = []
            calculations["active_model_count"] = 0
            calculations["supermajority_met"] = False
        else:
            model_inputs = raw_inputs
            trusted_classes = {"synthetic_test", "user_verified", "verified_local"}
            top_trust = model_inputs.get("input_trust_class", model_inputs.get("trust_class"))
            untrusted = False
            schema_invalid = False

            # Scan all provided model inputs for unverified or untrusted input trust class
            active_model_keys = [k for k in ("power_law", "markov", "bass", "bandit", "bandits") if k in model_inputs]
            if not active_model_keys and top_trust == "untrusted_external":
                untrusted = True
            for k in active_model_keys:
                entry = model_inputs[k]
                if not isinstance(entry, dict):
                    schema_invalid = True
                    break
                if entry.get("contract_version") == "nhi.model_input.v1":
                    from capital_decision_lab.contracts.validation import validate_contract
                    contract_issues = validate_contract(entry)
                    if contract_issues:
                        schema_invalid = True
                        break
                model_trust = entry.get("input_trust_class", entry.get("trust_class", top_trust))
                if model_trust not in trusted_classes:
                    untrusted = True
                    break

            if schema_invalid:
                flags.append("SCHEMA_INVALID_MODEL_INPUTS")
                flags.append("MALFORMED_MODEL_INPUTS")
                recommendation = "pause"
                calculations["trust_status"] = "rejected"
                calculations["binding_vetoes"] = ["SCHEMA_INVALID_MODEL_INPUTS"]
                calculations["compiled_claims"] = []
                calculations["active_model_count"] = 0
                calculations["supermajority_met"] = False
            elif untrusted:
                flags.append("UNTRUSTED_EXTERNAL_INPUT")
                recommendation = "pause"
                calculations["trust_status"] = "rejected"
                calculations["binding_vetoes"] = ["UNTRUSTED_EXTERNAL_INPUT"]
                calculations["compiled_claims"] = []
                calculations["active_model_count"] = 0
                calculations["supermajority_met"] = False
                vetoes.append("UNTRUSTED_EXTERNAL_INPUT")
            else:
                calculations["trust_status"] = "verified"

                # 1. Power Law Diagnostic
                if "power_law" in model_inputs and isinstance(model_inputs["power_law"], dict):
                    try:
                        from capital_decision_lab.calculations.power_law import fit_power_law_tail
                        pl_entry = model_inputs["power_law"]
                        pl_params = pl_entry.get("parameters", pl_entry) if isinstance(pl_entry, dict) else {}
                        obs = pl_params.get("observations", [])
                        xmin = float(pl_params.get("xmin", 1.0))
                        if not isinstance(obs, list) or not obs:
                            vetoes.append("HEAVY_TAIL_FIT_UNAVAILABLE")
                            flags.append("HEAVY_TAIL_FIT_UNAVAILABLE")
                        else:
                            pl_res = fit_power_law_tail(obs, xmin=xmin)
                            calculations["power_law_result"] = pl_res
                            alpha_val = pl_res.get("data", {}).get("alpha", {}).get("value")
                            if alpha_val is not None:
                                if float(alpha_val) <= 2.0:
                                    vetoes.append("HEAVY_TAIL_UNDEFINED_MEAN")
                                    flags.append("HEAVY_TAIL_UNDEFINED_MEAN")
                                elif float(alpha_val) <= 3.0:
                                    flags.append("HEAVY_TAIL_INFINITE_VARIANCE_ALLOWED")
                                    claims.append({
                                        "claim_id": "thesis_upside",
                                        "model_family": "power_law",
                                        "direction": "positive",
                                        "receipt_hash": pl_res.get("canonical_hash", "0" * 64),
                                    })
                                else:
                                    claims.append({
                                        "claim_id": "thesis_upside",
                                        "model_family": "power_law",
                                        "direction": "positive",
                                        "receipt_hash": pl_res.get("canonical_hash", "0" * 64),
                                    })
                            else:
                                vetoes.append("HEAVY_TAIL_FIT_UNAVAILABLE")
                                flags.append("HEAVY_TAIL_FIT_UNAVAILABLE")
                    except Exception:
                        vetoes.append("HEAVY_TAIL_FIT_UNAVAILABLE")
                        flags.append("HEAVY_TAIL_FIT_UNAVAILABLE")

                # 2. Markov Regime Diagnostic
                if "markov" in model_inputs and isinstance(model_inputs["markov"], dict):
                    try:
                        from capital_decision_lab.calculations.markov import compute_stationary_distribution
                        m_entry = model_inputs["markov"]
                        m_params = m_entry.get("parameters", m_entry) if isinstance(m_entry, dict) else {}
                        states = m_params.get("states", [])
                        matrix = m_params.get("transition_matrix", [])
                        if not states or not matrix:
                            flags.append("MARKOV_INPUTS_INVALID")
                        else:
                            m_res = compute_stationary_distribution(states=states, transition_matrix=matrix)
                            calculations["markov_result"] = m_res
                            stat_dist = m_res.get("data", {}).get("stationary_distribution", {}).get("value")
                            if isinstance(stat_dist, dict):
                                bull_prob = stat_dist.get("bull", stat_dist.get(states[-1] if states else "", 0.0))
                                if isinstance(bull_prob, (int, float)) and float(bull_prob) >= 0.50:
                                    claims.append({
                                        "claim_id": "thesis_upside",
                                        "model_family": "markov",
                                        "direction": "positive",
                                        "receipt_hash": m_res.get("canonical_hash", "0" * 64),
                                    })
                                else:
                                    claims.append({
                                        "claim_id": "thesis_upside",
                                        "model_family": "markov",
                                        "direction": "negative",
                                        "receipt_hash": m_res.get("canonical_hash", "0" * 64),
                                    })
                    except Exception:
                        flags.append("MARKOV_COMPUTATION_FAILED")

                # 3. Bass Diffusion Model
                if "bass" in model_inputs and isinstance(model_inputs["bass"], dict):
                    try:
                        from capital_decision_lab.calculations.bass import simulate_bass_diffusion
                        b_entry = model_inputs["bass"]
                        b_params = b_entry.get("parameters", b_entry) if isinstance(b_entry, dict) else {}
                        M = float(b_params.get("market_potential", b_params.get("M", 10000.0)))
                        p = float(b_params.get("innovation_rate", b_params.get("p", 0.03)))
                        q = float(b_params.get("imitation_rate", b_params.get("q", 0.38)))
                        horizon = int(b_params.get("horizon", 20))
                        init_adopters = float(b_params.get("initial_adopters", 0.0))
                        b_res = simulate_bass_diffusion(
                            market_potential=M,
                            innovation_rate=p,
                            imitation_rate=q,
                            initial_adopters=init_adopters,
                            horizon=horizon,
                        )
                        calculations["bass_result"] = b_res
                        total_adopters = b_res.get("data", {}).get("cumulative_adopters", {}).get("value")
                        if total_adopters and isinstance(total_adopters, list) and float(total_adopters[-1]) >= 0.30 * M:
                            claims.append({
                                "claim_id": "thesis_upside",
                                "model_family": "bass",
                                "direction": "positive",
                                "receipt_hash": b_res.get("canonical_hash", "0" * 64),
                            })
                    except Exception:
                        flags.append("BASS_COMPUTATION_FAILED")

                # 4. Multi-Armed Bandit Simulation
                bandit_entry = model_inputs.get("bandit") or model_inputs.get("bandits")
                if bandit_entry and isinstance(bandit_entry, dict):
                    try:
                        from capital_decision_lab.calculations.bandits import simulate_bernoulli_bandit
                        ban_params = bandit_entry.get("parameters", bandit_entry) if isinstance(bandit_entry, dict) else {}
                        probs = ban_params.get("arm_probabilities", ban_params.get("probabilities", [0.5, 0.5]))
                        horizon = int(ban_params.get("horizon", 50))
                        policy = str(ban_params.get("policy", "adaptive_epsilon"))
                        k_arms = max(1, len(probs))
                        init_pulls = max(1, min(10, horizon // (k_arms * 2)))
                        ban_res = simulate_bernoulli_bandit(
                            arm_probabilities=probs,
                            horizon=horizon,
                            policy=policy,
                            initial_pulls_per_arm=init_pulls,
                        )
                        calculations["bandit_result"] = ban_res
                        reward = ban_res.get("data", {}).get("total_reward", {}).get("value")
                        if reward is not None:
                            claims.append({
                                "claim_id": "thesis_upside",
                                "model_family": "bandits",
                                "direction": "positive",
                                "receipt_hash": ban_res.get("canonical_hash", "0" * 64),
                            })
                    except Exception:
                        flags.append("BANDIT_COMPUTATION_FAILED")

                # 5. Deterministic Claim Compiler
                from capital_decision_lab.ensemble.compiler import compile_claim_ensemble
                if claims:
                    ensemble_res = compile_claim_ensemble(claims, binding_vetoes=vetoes)
                    calculations["ensemble_result"] = ensemble_res
                    calculations["compiled_claims"] = claims
                    calculations["binding_vetoes"] = vetoes
                else:
                    calculations["ensemble_result"] = None
                    calculations["compiled_claims"] = []
                    calculations["binding_vetoes"] = vetoes

                if vetoes:
                    recommendation = "pause" if ("UNTRUSTED_EXTERNAL_INPUT" in vetoes or "SCHEMA_INVALID_MODEL_INPUTS" in vetoes) else "watch"
                    target = current
                elif calculations["ensemble_result"] and calculations["ensemble_result"].get("claims", {}).get("robust_positive"):
                    full = float(_value(analysis, "full_kelly_fraction"))
                    if full > current:
                        recommendation = "increase exposure under this assumption set"
                        target = full
                    elif full < current:
                        recommendation = "trim to fractional Kelly"
                        target = full
                    else:
                        recommendation = "hold current exposure"
                        target = current
                else:
                    recommendation = "watch"
                    target = current

    result = {
        "contract_version": "nhi.method_pack_result.v1",
        "result_id": f"method_result_{canonical_sha256([pack_id, contract_payload_hash(case_bundle)])[:16]}",
        "pack_id": pack_id, "pack_name": PACKS[pack_id]["display_name"],
        "case_hash": contract_payload_hash(case_bundle),
        "data": {
            "inputs_used": atom([name for name in ("portfolio", "thesis") if name not in missing], "calculated"),
            "missing_inputs": atom(sorted(set(missing)), "calculated"),
            "evidence_used": atom(evidence_used, "calculated"),
            "method_specific_calculations": atom(calculations, "calculated"),
            "red_flags": atom(flags, "modeled"), "recommendation_modifiers": atom(modifiers, "modeled"),
            "model_implied_recommendation": atom(recommendation, "modeled"),
            "target_exposure": atom(target, "modeled", unit="capital fraction"),
            "full_kelly": atom(float(_value(analysis, "full_kelly_fraction")), "calculated", unit="capital fraction"),
            "confidence": atom(confidence, "modeled", unit="score"),
        },
        "limitations": PACKS[pack_id]["limitations"], "required_user_authorization": True,
    }
    result["canonical_hash"] = contract_payload_hash(result)
    return result


ALLOWED_COMMITTEE_RECOMMENDATIONS = {
    "avoid margin",
    "pause",
    "watch",
    "hold current exposure",
    "trim to fractional Kelly",
    "increase exposure under this assumption set",
}

COMMITTEE_PRIORITY_ORDER = [
    "avoid margin",
    "pause",
    "watch",
    "hold current exposure",
    "trim to fractional Kelly",
    "increase exposure under this assumption set",
]


def run_committee(pack_ids: list[str], case_bundle: dict) -> dict:
    if not pack_ids:
        raise ValueError("METHOD_PACKS_REQUIRED")
    results = [run_method_pack(pack_id, case_bundle) for pack_id in pack_ids]
    recommendations = [item["data"]["model_implied_recommendation"]["value"] for item in results]

    for rec in recommendations:
        if not isinstance(rec, str) or rec not in ALLOWED_COMMITTEE_RECOMMENDATIONS:
            raise ValueError("UNKNOWN_RECOMMENDATION_OUTPUT")

    agreement = len(set(recommendations)) == 1
    synthesis = next((item for item in COMMITTEE_PRIORITY_ORDER if item in recommendations), None)
    if synthesis is None:
        raise ValueError("UNKNOWN_RECOMMENDATION_OUTPUT")

    binding = next((item["pack_id"] for item in results if item["data"]["model_implied_recommendation"]["value"] == synthesis), results[0]["pack_id"])
    document = {
        "contract_version": "nhi.committee_result.v1",
        "committee_id": f"committee_{canonical_sha256([pack_ids, contract_payload_hash(case_bundle)])[:16]}",
        "pack_results": results,
        "data": {
            "agreement": atom(agreement, "calculated"),
            "disagreement": atom([] if agreement else recommendations, "calculated"),
            "strongest_add_case": atom(next((item["pack_id"] for item in results if item["data"]["model_implied_recommendation"]["value"] == "increase exposure under this assumption set"), None), "modeled"),
            "strongest_trim_case": atom(next((item["pack_id"] for item in results if item["data"]["model_implied_recommendation"]["value"] in {"avoid margin", "trim to fractional Kelly"}), None), "modeled"),
            "strongest_hold_watch_case": atom(next((item["pack_id"] for item in results if item["data"]["model_implied_recommendation"]["value"] in {"hold current exposure", "watch", "pause"}), None), "modeled"),
            "binding_constraint": atom(binding, "modeled"),
            "hermes_synthesis": atom(synthesis, "modeled"),
        },
        "required_user_action": "Review the synthesis and explicitly authorize any decision record.",
        "required_user_authorization": True,
    }
    document["canonical_hash"] = contract_payload_hash(document)
    return document
