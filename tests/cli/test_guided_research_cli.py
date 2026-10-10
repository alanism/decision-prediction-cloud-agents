from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.plugin.commands import run_cli
from tests.recommendation.test_recommendation_engine import inputs
from tests.recommendation.test_recommendation_record import authorization


def write(root: Path, name: str, value: dict) -> Path:
    path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_portfolio_research_and_manual_evidence_commands(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    portfolio = inputs()["portfolio"]
    portfolio_path = write(local, "portfolio.json", portfolio)
    for argv in (
        ["portfolio", "validate", "--file", str(portfolio_path)],
        ["portfolio", "import", "--file", str(portfolio_path)],
        ["thesis", "start", "--portfolio", str(portfolio_path)],
        ["evidence", "gather", "--case", str(portfolio_path), "--source", "manual_note", "--query", "Synthetic verified note"],
        ["research", "loop", "--case", str(portfolio_path)],
    ):
        code, result = run_cli(argv, local_root=local)
        assert code in {0, 3}, result
        assert result["status"] in {"ok", "blocked_missing_user_input"}


def test_model_health_recommend_and_decision_record(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    recommendation_inputs = inputs()
    case = write(local, "recommendation-inputs.json", recommendation_inputs)
    health_input = write(local, "health.json", {"contradiction": 0.1, "edge_compression": 0.1, "drawdown_ratio": 0.4, "margin_stress": 0.1, "kill_condition_triggered": False, "confidence": 0.9, "staleness": 0.1})
    code, health = run_cli(["model-health", "check", "--case", str(case), "--evidence", str(health_input)], local_root=local)
    assert code == 0 and health["model_health"]["state"] == "healthy"
    code, recommended = run_cli(["recommend", "--case", str(case)], local_root=local)
    assert code == 0
    recommendation = recommended["recommendation"]
    recommendation_path = write(local, "recommendation.json", recommendation)
    auth = authorization(recommendation)
    auth_path = write(local, "recommendation-authorization.json", auth)
    code, recorded = run_cli(["decision", "record", "--recommendation", str(recommendation_path), "--authorization", str(auth_path)], local_root=local)
    assert code == 0 and recorded["appended"] is True


def test_evidence_verify_does_not_mutate_source_file(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    item = {"verification_status": "unverified_extraction", "source_type": "x_twitter", "content": {"text": "Synthetic"}}
    path = write(local, "item.json", item)
    original = path.read_text(encoding="utf-8")
    code, result = run_cli(["evidence", "verify", "--item", str(path)], local_root=local)
    assert code == 0
    assert result["verified_item"]["verification_status"] == "user_verified"
    assert path.read_text(encoding="utf-8") == original
