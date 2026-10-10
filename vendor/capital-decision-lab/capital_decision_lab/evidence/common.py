"""Shared evidence atoms and bounded numeric helpers."""

from __future__ import annotations

from typing import Any


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def atom(
    value: Any,
    provenance_class: str,
    *,
    unit: str | None = None,
    input_refs: list[str] | None = None,
    formula_ref: str | None = None,
    limitations: list[str] | None = None,
) -> dict:
    result = {"value": value, "provenance_class": provenance_class}
    if unit is not None:
        result["unit"] = unit
    if input_refs:
        result["input_refs"] = input_refs
    if formula_ref is not None:
        result["formula_ref"] = formula_ref
    if limitations:
        result["limitations"] = limitations
    return result


def atom_value(document: dict, name: str, default: Any = 0.0) -> Any:
    candidate = document.get("data", {}).get(name, {})
    return candidate.get("value", default) if isinstance(candidate, dict) else default
