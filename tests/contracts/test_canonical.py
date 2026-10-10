from __future__ import annotations

from capital_decision_lab.contracts import canonical


def test_canonical_serialization_is_stable_across_key_order() -> None:
    left = {"b": 2, "a": {"y": 1, "x": 0}}
    right = {"a": {"x": 0, "y": 1}, "b": 2}
    assert canonical.canonical_json(left) == canonical.canonical_json(right)
    assert canonical.canonical_sha256(left) == canonical.canonical_sha256(right)


def test_canonical_hash_changes_with_semantic_value() -> None:
    assert canonical.canonical_sha256({"value": 1}) != canonical.canonical_sha256({"value": 2})


def test_contract_payload_hash_excludes_only_root_hash_field() -> None:
    first = {"contract_version": "nhi.example.v1", "value": 1, "canonical_hash": "old"}
    second = {"canonical_hash": "new", "value": 1, "contract_version": "nhi.example.v1"}
    assert canonical.contract_payload_hash(first) == canonical.contract_payload_hash(second)

