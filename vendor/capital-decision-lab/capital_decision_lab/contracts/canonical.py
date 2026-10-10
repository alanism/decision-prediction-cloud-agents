"""Deterministic JSON serialization and SHA-256 contract hashing."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Return UTF-8-safe canonical JSON with stable object-key ordering."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    """Hash the UTF-8 bytes of canonical JSON."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def contract_payload_hash(document: dict) -> str:
    """Hash a contract after excluding only its root canonical-hash field."""
    if not isinstance(document, dict):
        raise TypeError("CONTRACT_DOCUMENT_NOT_OBJECT")
    payload = copy.deepcopy(document)
    payload.pop("canonical_hash", None)
    return canonical_sha256(payload)
