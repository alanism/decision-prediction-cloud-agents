"""Explicit thesis-specific event direction mapping."""

from __future__ import annotations


_WEIGHTS = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}


def match_sensitivity(synthesis: dict, sensitivity_map: dict) -> dict:
    for context in synthesis.get("source_contexts", []):
        channels = set(context.get("impact_channels", []))
        for rule in sensitivity_map.get("sensitivity_rules", []):
            if (
                rule.get("source_type") == context.get("source_type")
                and rule.get("event_domain") == context.get("event_domain")
                and rule.get("event_category") == context.get("event_category")
                and rule.get("impact_channel") in channels
            ):
                return {
                    "matched": True, "direction_for_thesis": rule["direction_for_thesis"],
                    "sensitivity": rule["sensitivity"], "weight_multiplier": _WEIGHTS[rule["sensitivity"]],
                    "affected_assumption": rule["affected_assumption"], "impact_channel": rule["impact_channel"],
                }
    return {
        "matched": False, "direction_for_thesis": "unknown", "sensitivity": "low",
        "weight_multiplier": 0.0, "affected_assumption": None, "impact_channel": None,
    }
