from __future__ import annotations

from capital_decision_lab.contracts import validation


def test_complete_evidence_atom_is_valid() -> None:
    atom = {
        "value": 1250.0,
        "provenance_class": "calculated",
        "unit": "USD",
        "input_refs": ["input.amount"],
        "formula_ref": "formula.example.v1",
        "limitations": ["Synthetic contract fixture"],
    }
    assert validation.validate_evidence_atom(atom) == []


def test_missing_provenance_class_fails() -> None:
    issues = validation.validate_evidence_atom({"value": 1})
    assert issues == [{"code": "PROVENANCE_CLASS_MISSING", "path": "$"}]


def test_invalid_provenance_class_fails() -> None:
    issues = validation.validate_evidence_atom({"value": 1, "provenance_class": "derived"})
    assert issues == [{"code": "PROVENANCE_CLASS_INVALID", "path": "$.provenance_class"}]


def test_plain_semantic_leaf_fails() -> None:
    issues = validation.validate_evidence_atom(42, path="$.data.result")
    assert issues == [{"code": "EVIDENCE_ATOM_REQUIRED", "path": "$.data.result"}]


def test_unavailable_requires_reason() -> None:
    issues = validation.validate_evidence_atom(
        {"value": None, "provenance_class": "unavailable"}
    )
    assert issues == [{"code": "UNAVAILABLE_REASON_REQUIRED", "path": "$.reason"}]


def test_unavailable_result_has_required_structure() -> None:
    result = validation.unavailable_result(
        "insufficient inputs",
        unit="USD",
        input_refs=["input.amount"],
        limitations=["No substitute value supplied"],
    )
    assert result == {
        "value": None,
        "provenance_class": "unavailable",
        "reason": "insufficient inputs",
        "unit": "USD",
        "input_refs": ["input.amount"],
        "limitations": ["No substitute value supplied"],
    }
    assert validation.validate_evidence_atom(result) == []

