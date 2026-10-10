"""Standard-library validation for versioned decision contracts."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_ROOT = Path(__file__).resolve().parents[4] / "schemas"
PROVENANCE_CLASSES = (
    "measured",
    "assumed",
    "calculated",
    "modeled",
    "forecast",
    "decided",
    "unavailable",
)
_SCHEMA_FILES = {
    "nhi.assumption_update_proposal.v1": "assumption-update-proposal.v1.schema.json",
    "nhi.assumption_register.v1": "assumption-register.v1.schema.json",
    "nhi.bayesian_update.v1": "bayesian-update.v1.schema.json",
    "nhi.belief_state.v1": "belief-state.v1.schema.json",
    "nhi.decision_analysis.v1": "decision-analysis.v1.schema.json",
    "nhi.decision_authorization.v1": "decision-authorization.v1.schema.json",
    "nhi.decision_case.v1": "decision-case.v1.schema.json",
    "nhi.decision_comparison.v1": "decision-comparison.v1.schema.json",
    "nhi.decision_ledger.v1": "decision-ledger.v1.schema.json",
    "nhi.decision_proposal.v1": "decision-proposal.v1.schema.json",
    "nhi.evidence_batch.v1": "evidence-batch.v1.schema.json",
    "nhi.evidence_item.v1": "evidence-item.v1.schema.json",
    "nhi.evidence_source.v1": "evidence-source.v1.schema.json",
    "nhi.event_market_signal.v1": "event-market-signal.v1.schema.json",
    "nhi.event_market_snapshot.v1": "event-market-snapshot.v1.schema.json",
    "nhi.host_capability_request.v1": "host-capability-request.v1.schema.json",
    "nhi.host_capability_response.v1": "host-capability-response.v1.schema.json",
    "nhi.host_extraction_result.v1": "host-extraction-result.v1.schema.json",
    "nhi.host_source_artifact.v1": "host-source-artifact.v1.schema.json",
    "nhi.host_user_confirmation.v1": "host-user-confirmation.v1.schema.json",
    "nhi.portfolio_intent.v1": "portfolio-intent.v1.schema.json",
    "nhi.portfolio_position.v1": "portfolio-position.v1.schema.json",
    "nhi.portfolio_snapshot.v1": "portfolio-snapshot.v1.schema.json",
    "nhi.recommendation.v1": "recommendation.v1.schema.json",
    "nhi.recommendation_authorization.v1": "recommendation-authorization.v1.schema.json",
    "nhi.scenario_assumption.v1": "scenario-assumption.v1.schema.json",
    "nhi.social_evidence_signal.v1": "social-evidence-signal.v1.schema.json",
    "nhi.stock_thesis.v1": "stock-thesis.v1.schema.json",
    "nhi.kill_condition.v1": "kill-condition.v1.schema.json",
    "nhi.thesis_sensitivity_map.v1": "thesis-sensitivity-map.v1.schema.json",
    "nhi.model_input.v1": "model-input.v1.schema.json",
    "nhi.model_result.v1": "model-result.v1.schema.json",
    "nhi.ensemble_result.v1": "ensemble-result.v1.schema.json",
    "nhi.method_pack.v1": "method-pack.v1.schema.json",
    "nhi.method_pack_run.v1": "method-pack-run.v1.schema.json",
    "nhi.method_pack_result.v1": "method-pack-result.v1.schema.json",
    "nhi.committee_result.v1": "committee-result.v1.schema.json",
}
_ATOM_PROPERTIES = {
    "value",
    "provenance_class",
    "unit",
    "input_refs",
    "formula_ref",
    "limitations",
    "reason",
}


def _issue(code: str, path: str) -> dict[str, str]:
    return {"code": code, "path": path}


def supported_contract_versions() -> tuple[str, ...]:
    return tuple(sorted(_SCHEMA_FILES))


def load_schema(version: str, *, schema_root: Path | None = None) -> dict:
    """Load an allowlisted schema by exact contract version."""
    filename = _SCHEMA_FILES.get(version)
    if filename is None:
        raise ValueError("CONTRACT_VERSION_UNKNOWN")
    root = Path(schema_root or SCHEMA_ROOT).resolve(strict=True)
    path = (root / filename).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("SCHEMA_PATH_ESCAPE") from exc
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("SCHEMA_LOAD_FAILED") from exc
    expected = schema.get("properties", {}).get("contract_version", {}).get("const")
    if expected != version:
        raise ValueError("SCHEMA_VERSION_IDENTITY_MISMATCH")
    return schema


def unavailable_result(
    reason: str,
    *,
    unit: str | None = None,
    input_refs: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict:
    """Construct an explicitly unavailable evidence atom without a substitute value."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("UNAVAILABLE_REASON_REQUIRED")
    result: dict[str, Any] = {
        "value": None,
        "provenance_class": "unavailable",
        "reason": reason,
    }
    if unit is not None:
        result["unit"] = unit
    if input_refs is not None:
        result["input_refs"] = list(input_refs)
    if limitations is not None:
        result["limitations"] = list(limitations)
    return result


def validate_evidence_atom(value: Any, *, path: str = "$") -> list[dict[str, str]]:
    """Validate one semantic output value and its epistemic provenance."""
    if not isinstance(value, dict):
        return [_issue("EVIDENCE_ATOM_REQUIRED", path)]
    if "provenance_class" not in value:
        return [_issue("PROVENANCE_CLASS_MISSING", f"{path}.provenance_class" if path != "$" else "$")]
    provenance = value["provenance_class"]
    if provenance not in PROVENANCE_CLASSES:
        return [_issue("PROVENANCE_CLASS_INVALID", f"{path}.provenance_class")]

    issues: list[dict[str, str]] = []
    if "value" not in value:
        issues.append(_issue("EVIDENCE_VALUE_MISSING", f"{path}.value"))
    extras = sorted(set(value) - _ATOM_PROPERTIES)
    issues.extend(_issue("EVIDENCE_PROPERTY_UNKNOWN", f"{path}.{name}") for name in extras)
    if "unit" in value and not isinstance(value["unit"], str):
        issues.append(_issue("EVIDENCE_UNIT_INVALID", f"{path}.unit"))
    if "formula_ref" in value and not isinstance(value["formula_ref"], str):
        issues.append(_issue("EVIDENCE_FORMULA_REF_INVALID", f"{path}.formula_ref"))
    for name in ("input_refs", "limitations"):
        if name in value and (
            not isinstance(value[name], list)
            or any(not isinstance(item, str) for item in value[name])
        ):
            issues.append(_issue("EVIDENCE_LIST_INVALID", f"{path}.{name}"))
    if provenance == "unavailable":
        if value.get("value", object()) is not None:
            issues.append(_issue("UNAVAILABLE_VALUE_INVALID", f"{path}.value"))
        reason = value.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            issues.append(_issue("UNAVAILABLE_REASON_REQUIRED", f"{path}.reason"))
    return issues


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _resolve_local_ref(root_schema: dict, reference: str) -> dict:
    if not reference.startswith("#/"):
        raise ValueError("EXTERNAL_SCHEMA_REF_FORBIDDEN")
    current: Any = root_schema
    for token in reference[2:].split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            raise ValueError("SCHEMA_REF_INVALID")
        current = current[key]
    if not isinstance(current, dict):
        raise ValueError("SCHEMA_REF_INVALID")
    return current


def _validate_schema_node(
    value: Any,
    schema: dict,
    *,
    root_schema: dict,
    path: str,
) -> list[dict[str, str]]:
    if "$ref" in schema:
        return _validate_schema_node(
            value,
            _resolve_local_ref(root_schema, schema["$ref"]),
            root_schema=root_schema,
            path=path,
        )

    issues: list[dict[str, str]] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = [expected_type] if isinstance(expected_type, str) else expected_type
        if not any(_matches_type(value, item) for item in allowed):
            return [_issue("SCHEMA_TYPE_INVALID", path)]
    if "const" in schema and value != schema["const"]:
        issues.append(_issue("SCHEMA_CONST_MISMATCH", path))
    if "enum" in schema and value not in schema["enum"]:
        issues.append(_issue("SCHEMA_ENUM_INVALID", path))

    if isinstance(value, dict):
        required = schema.get("required", [])
        issues.extend(
            _issue("SCHEMA_REQUIRED_MISSING", f"{path}.{name}")
            for name in required
            if name not in value
        )
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for name, item in value.items():
            child_path = f"{path}.{name}"
            if name in properties:
                issues.extend(
                    _validate_schema_node(
                        item,
                        properties[name],
                        root_schema=root_schema,
                        path=child_path,
                    )
                )
            elif additional is False:
                issues.append(_issue("SCHEMA_ADDITIONAL_PROPERTY", child_path))
            elif isinstance(additional, dict):
                issues.extend(
                    _validate_schema_node(
                        item,
                        additional,
                        root_schema=root_schema,
                        path=child_path,
                    )
                )
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            issues.append(_issue("SCHEMA_MIN_ITEMS", path))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                issues.extend(
                    _validate_schema_node(
                        item,
                        item_schema,
                        root_schema=root_schema,
                        path=f"{path}[{index}]",
                    )
                )
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            issues.append(_issue("SCHEMA_MIN_LENGTH", path))
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            issues.append(_issue("SCHEMA_PATTERN_INVALID", path))

    for part in schema.get("allOf", []):
        issues.extend(
            _validate_schema_node(value, part, root_schema=root_schema, path=path)
        )
    conditional = schema.get("if")
    if isinstance(conditional, dict):
        condition_issues = _validate_schema_node(
            value, conditional, root_schema=root_schema, path=path
        )
        branch = schema.get("then") if not condition_issues else schema.get("else")
        if isinstance(branch, dict):
            issues.extend(
                _validate_schema_node(value, branch, root_schema=root_schema, path=path)
            )
    return issues


def validate_contract(document: Any, *, schema_root: Path | None = None) -> list[dict[str, str]]:
    """Validate schema structure plus evidence-atom invariants."""
    if not isinstance(document, dict):
        return [_issue("CONTRACT_DOCUMENT_NOT_OBJECT", "$")]
    version = document.get("contract_version")
    if not isinstance(version, str) or version not in _SCHEMA_FILES:
        return [_issue("CONTRACT_VERSION_UNKNOWN", "$.contract_version")]
    try:
        schema = load_schema(version, schema_root=schema_root)
        issues = _validate_schema_node(document, schema, root_schema=schema, path="$")
    except ValueError as exc:
        return [_issue(str(exc), "$")]

    if version in {
        "nhi.decision_analysis.v1",
        "nhi.decision_comparison.v1",
        "nhi.event_market_signal.v1",
        "nhi.social_evidence_signal.v1",
        "nhi.bayesian_update.v1",
        "nhi.model_result.v1",
    }:
        data = document.get("data")
        if isinstance(data, dict):
            for name, atom in data.items():
                issues.extend(validate_evidence_atom(atom, path=f"$.data.{name}"))
    elif version == "nhi.decision_proposal.v1" and "selected_action" in document:
        issues.extend(
            validate_evidence_atom(document["selected_action"], path="$.selected_action")
        )

    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for issue in issues:
        key = (issue["code"], issue["path"])
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique
