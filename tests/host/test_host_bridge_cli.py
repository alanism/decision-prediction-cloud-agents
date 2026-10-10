from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.host.bridge import analysis_eligibility, ingest_capability_response
from capital_decision_lab.plugin.commands import run_cli
from tests.host.test_source_extractors import response


def write(root: Path, name: str, value: dict) -> Path:
    path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def market_response(method: str = "browser") -> dict:
    fields = {"market_title": "Will rates be cut?", "event_category": "rate_cut", "resolution_date": "2026-08-01", "resolution_rules": "Synthetic rule", "total_volume": 50000, "outcomes": [{"name": "Yes", "probability": 0.6}, {"name": "No", "probability": 0.4}]}
    return response("market", fields, method=method)


def test_ingest_records_provenance_but_generic_response_is_not_analysis_eligible() -> None:
    host_response = market_response()
    ingested = ingest_capability_response(host_response)
    assert ingested["retrieval_method"] == "browser"
    assert ingested["retrieval_timestamp"]
    assert ingested["source_url"]
    assert ingested["raw_content_hash"] == "b" * 64
    assert analysis_eligibility(host_response)["eligible"] is False
    assert analysis_eligibility(host_response)["issues"] == [{"code": "SOURCE_SPECIFIC_EXTRACTION_REQUIRED"}]


def test_host_capabilities_ingest_and_extract_commands(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    case = write(local, "case.json", {"inputs": {}})
    raw = write(local, "response.json", market_response())
    code, capabilities = run_cli(["host", "capabilities"], local_root=local)
    assert code == 0 and "screenshot_ocr" in capabilities["capabilities"]
    code, ingested = run_cli(["host", "ingest", "--capability-response", str(raw)], local_root=local)
    assert code == 0 and ingested["host_response"]["raw_content_hash"] == "b" * 64
    code, extracted = run_cli(["host", "extract", "--source", "polymarket", "--input", str(raw)], local_root=local)
    assert code == 0
    assert extracted["extraction_bundle"]["document"]["contract_version"] == "nhi.event_market_snapshot.v1"
    assert analysis_eligibility(extracted["extraction_bundle"]["extraction"])["eligible"] is True


def test_host_confirm_and_research_run(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    raw = write(local, "response.json", market_response("screenshot"))
    _, extracted = run_cli(["host", "extract", "--source", "polymarket", "--input", str(raw)], local_root=local)
    bundle = extracted["extraction_bundle"]
    bundle_path = write(local, "host-inputs/extraction.json", bundle)
    confirmation = {"contract_version": "nhi.host_user_confirmation.v1", "confirmation_id": "confirm_1", "extraction_ref": {"extraction_id": bundle["extraction"]["extraction_id"], "canonical_hash": bundle["extraction"]["canonical_hash"]}, "action": "confirm", "corrections": {}, "confirmed_by_human": True}
    from capital_decision_lab.contracts.canonical import contract_payload_hash
    confirmation["canonical_hash"] = contract_payload_hash(confirmation)
    confirmation_path = write(local, "confirmation.json", confirmation)
    code, confirmed = run_cli(["host", "confirm", "--extraction", str(bundle_path), "--confirmation", str(confirmation_path)], local_root=local)
    assert code == 0 and confirmed["extraction_bundle"]["extraction"]["verification_status"] == "user_verified"
    write(local, "host-inputs/extraction.json", confirmed["extraction_bundle"])
    case = write(local, "case.json", {"inputs": {"win_probability": 0.6, "upside_payoff": 1, "downside_loss": 0.5, "capital_at_risk": 1000, "max_exposure_cap": 0.1, "maintenance_margin_requirement": 0.25, "borrowed_amount": 0, "current_price": 100, "shares": 10}})
    code, result = run_cli(["research", "run", "--case", str(case), "--host-inputs", str(local / "host-inputs")], local_root=local)
    assert code == 0 and result["status"] == "analysis_ready"


def test_failed_extraction_returns_actionable_loop(tmp_path: Path) -> None:
    local = tmp_path / "local"; local.mkdir()
    bad = response("post", {"author_handle": "missing_text"})
    path = write(local, "bad.json", bad)
    code, result = run_cli(["host", "extract", "--source", "x_twitter", "--input", str(path)], local_root=local)
    assert code == 3
    assert result["status"] == "blocked_missing_user_input"
    assert result["mini_loop"]["code"] == "X_TWITTER_CONFIRMATION_REQUIRED"
