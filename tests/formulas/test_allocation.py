from __future__ import annotations

import pytest

from capital_decision_lab.calculations import allocation
from capital_decision_lab.contracts.validation import validate_evidence_atom


def _value(atom: dict) -> float:
    assert validate_evidence_atom(atom) == []
    return atom["value"]


def test_kelly_fractional_and_capped_fractional() -> None:
    assert _value(allocation.kelly(0.6, 1.0)) == pytest.approx(0.2)
    assert _value(allocation.fractional_kelly(0.6, 1.0, 0.5)) == pytest.approx(0.1)
    assert _value(allocation.capped_fractional_kelly(0.6, 1.0, 0.5, 0.05)) == pytest.approx(0.05)


def test_capped_fractional_does_not_create_negative_exposure() -> None:
    assert _value(allocation.kelly(0.4, 1.0)) == pytest.approx(-0.2)
    assert _value(allocation.capped_fractional_kelly(0.4, 1.0, 0.5, 0.25)) == 0.0


def test_invalid_allocation_inputs_are_unavailable() -> None:
    cases = [
        allocation.kelly(-0.1, 1.0),
        allocation.kelly(1.1, 1.0),
        allocation.kelly(0.6, 0.0),
        allocation.fractional_kelly(0.6, 1.0, 0.0),
        allocation.capped_fractional_kelly(0.6, 1.0, 0.5, -0.1),
    ]
    assert all(item["provenance_class"] == "unavailable" for item in cases)
    assert all(item["value"] is None for item in cases)
