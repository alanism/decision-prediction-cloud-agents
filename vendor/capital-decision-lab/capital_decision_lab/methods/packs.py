"""Declarative first-party method-pack definitions."""

COMMON_SECTIONS = ["pack_name", "inputs_used", "missing_inputs", "evidence_used", "method_specific_calculations", "method_specific_red_flags", "recommendation_modifiers", "model_implied_recommendation", "confidence", "limitations"]


PACKS = {
    "core": {
        "display_name": "Core", "description": "Fast default decision workflow.",
        "required_inputs": ["portfolio", "thesis"], "preferred_sources": ["polymarket", "x_twitter", "reddit", "manual_note"],
        "workflow_steps": ["portfolio", "thesis", "evidence", "bayesian_update", "kelly", "convexity", "margin", "model_health", "recommendation"],
        "mini_loop_rules": ["request_missing_required_input"], "calculation_modules": ["kelly", "convexity", "margin"],
        "rubric_dimensions": ["edge", "asymmetry", "survival"], "recommendation_modifiers": [],
        "report_sections": COMMON_SECTIONS, "limitations": ["Uses only supplied and verified inputs."],
    },
    "thorp": {
        "display_name": "Thorp", "description": "Sizing, survival, and edge-compression process.",
        "required_inputs": ["portfolio", "thesis", "kelly_stock", "margin_inputs"], "preferred_sources": ["portfolio", "broker_margin"],
        "workflow_steps": ["estimate_edge", "fractional_kelly", "leverage_cap", "margin_survival", "model_health"],
        "mini_loop_rules": ["request_odds", "request_margin"], "calculation_modules": ["kelly", "margin", "convexity"],
        "rubric_dimensions": ["edge", "survival", "capital_recycling"], "recommendation_modifiers": ["half_kelly_default", "quarter_kelly_weak_evidence", "margin_override"],
        "report_sections": COMMON_SECTIONS, "limitations": ["Sizing is conditional on supplied probability and payoff assumptions."],
    },
    "mauboussin": {
        "display_name": "Mauboussin", "description": "Outside-view and expectations process.",
        "required_inputs": ["portfolio", "thesis", "numerical_probabilities"], "preferred_sources": ["filings", "polymarket"],
        "workflow_steps": ["base_rates", "outside_view", "market_expectations", "scenario_ev", "premortem", "signposts"],
        "mini_loop_rules": ["request_probabilities", "request_base_rate"], "calculation_modules": ["returns", "convexity"],
        "rubric_dimensions": ["base_rate", "expectations", "calibration"], "recommendation_modifiers": ["overconfidence_flag", "kill_criteria_gate"],
        "report_sections": COMMON_SECTIONS, "limitations": ["Reverse valuation readiness requires user-supplied valuation inputs."],
    },
    "contrarian_filings": {
        "display_name": "Contrarian Filings", "description": "Primary-source balance-sheet and cash-flow process.",
        "required_inputs": ["portfolio", "thesis", "primary_filings"], "preferred_sources": ["filings"],
        "workflow_steps": ["filings", "enterprise_value", "cash_debt", "cash_flow", "market_expectations"],
        "mini_loop_rules": ["request_primary_filing"], "calculation_modules": ["returns", "convexity"],
        "rubric_dimensions": ["cash_flow", "dilution", "downside_support"], "recommendation_modifiers": ["missing_filings_gate", "dilution_risk", "asset_support"],
        "report_sections": COMMON_SECTIONS, "limitations": ["No filing facts are created when primary evidence is absent."],
    },
    "committee": {
        "display_name": "Committee", "description": "Compares selected method-pack outputs.",
        "required_inputs": ["selected_packs"], "preferred_sources": [], "workflow_steps": ["run_packs", "compare", "synthesize"],
        "mini_loop_rules": ["request_selected_packs"], "calculation_modules": [], "rubric_dimensions": ["agreement", "disagreement", "binding_constraint"],
        "recommendation_modifiers": ["most_conservative_binding_constraint"], "report_sections": COMMON_SECTIONS,
        "limitations": ["Synthesis does not replace user authorization."],
    },
    "page": {
        "display_name": "Scott Page Many-Model",
        "description": "Multi-model thinking and ensemble claim aggregation process.",
        "required_inputs": ["portfolio", "thesis"],
        "preferred_sources": ["filings", "polymarket", "x_twitter", "manual_note"],
        "workflow_steps": ["power_law", "markov", "bass", "bandit", "claim_compiler", "recommendation"],
        "mini_loop_rules": ["request_model_inputs"],
        "calculation_modules": ["power_law", "markov", "bass", "bandits", "compiler"],
        "rubric_dimensions": ["model_diversity", "tail_risk", "regime_stability", "diffusion_runway"],
        "recommendation_modifiers": ["heavy_tail_undefined_mean_gate", "supermajority_claim_support", "binding_veto_override"],
        "report_sections": COMMON_SECTIONS,
        "limitations": ["Many-model ensemble claims require independent mathematical models and user confirmation."],
    },
}
