from __future__ import annotations

import hashlib
from pathlib import Path

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.research.portfolio import import_portfolio_file, validate_portfolio_snapshot
from capital_decision_lab.research.thesis import structure_thesis


def portfolio(status: str = "user_verified") -> dict:
    return {
        "contract_version": "nhi.portfolio_snapshot.v1", "snapshot_id": "portfolio_1",
        "capture_timestamp": "2026-07-03T00:00:00Z", "cash": 2000.0,
        "total_equity": 10000.0, "margin_used": 0.0, "borrowed_amount": 0.0,
        "maintenance_margin_requirement": 0.25, "initial_margin_requirement": 0.5,
        "portfolio_source": "manual", "verification_status": status,
        "positions": [{
            "ticker": "SYNTH", "shares": 80.0, "current_price": 100.0,
            "market_value": 8000.0, "position_weight": 0.8, "user_intent": "hold",
            "max_position_cap": 0.5,
        }],
    }


def test_portfolio_snapshot_and_position_validate() -> None:
    assert validate_contract(portfolio()) == []
    position = {"contract_version": "nhi.portfolio_position.v1", **portfolio()["positions"][0]}
    assert validate_contract(position) == []


def test_invalid_portfolio_verification_fails() -> None:
    assert "SCHEMA_ENUM_INVALID" in {issue["code"] for issue in validate_contract(portfolio("model_verified"))}


def test_portfolio_screenshot_artifact_hash_is_verified(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    screenshot = local / "synthetic-screen.png"; screenshot.write_bytes(b"synthetic screenshot bytes")
    document = portfolio()
    document.update({"portfolio_source": "screenshot", "source_artifact_path": "synthetic-screen.png", "source_artifact_hash": hashlib.sha256(screenshot.read_bytes()).hexdigest()})
    assert validate_portfolio_snapshot(document, local) == []
    document["source_artifact_hash"] = "0" * 64
    assert {issue["code"] for issue in validate_portfolio_snapshot(document, local)} == {"PORTFOLIO_ARTIFACT_HASH_MISMATCH"}


def test_csv_portfolio_import_calculates_snapshot_without_inventing_fields(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.csv"
    path.write_text(
        "ticker,shares,current_price,user_intent,cash,borrowed_amount,maintenance_margin_requirement,initial_margin_requirement\n"
        "SYNTH,10,100,hold,500,0,0.25,0.5\n",
        encoding="utf-8",
    )
    result = import_portfolio_file(path)
    assert result["status"] == "ok"
    snapshot = result["portfolio"]
    assert snapshot["positions"][0]["market_value"] == 1000.0
    assert snapshot["total_equity"] == 1500.0
    assert snapshot["verification_status"] == "unverified_extraction"


def test_freeform_thesis_becomes_pending_structured_assumptions() -> None:
    thesis = structure_thesis(
        target_ticker="SYNTH", thesis_text="Synthetic upside depends on product delivery.",
        time_horizon="18 months",
    )
    assert thesis["confirmation_status"] == "pending"
    assert thesis["user_thesis_text"] == "Synthetic upside depends on product delivery."
    assert thesis["probabilities"] is None
    assert thesis["payoffs"] is None
