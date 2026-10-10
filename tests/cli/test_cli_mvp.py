from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.plugin.commands import run_cli
from capital_decision_lab.privacy.scanner import scan_text
from tests.orchestration.test_record import _write_documents


ROOT = Path(__file__).resolve().parents[2]


def _local_case(local_root: Path) -> Path:
    path = local_root / "cases" / "case.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        (ROOT / "fixtures" / "valid" / "mvp-case.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return path


def test_validate_analyze_and_compare_commands(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    case_path = _local_case(local_root)
    validate_code, validate_result = run_cli(["validate", "--synthetic"], local_root=local_root)
    analyze_code, analyze_result = run_cli(["analyze", "--case", str(case_path)], local_root=local_root)
    compare_code, compare_result = run_cli(["compare", "--case", str(case_path)], local_root=local_root)
    assert validate_code == analyze_code == compare_code == 0
    assert validate_result["validated_contracts"] == 7
    assert analyze_result["analysis"]["data"]
    assert len(compare_result["analyses"]) == 2
    for result in (validate_result, analyze_result, compare_result):
        assert result["network_attempts"] == 0
        assert result["model_calls"] == 0


def test_record_command_and_idempotent_replay(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    analysis_path, authorization_path = _write_documents(local_root)
    args = ["record", "--analysis", str(analysis_path), "--authorization", str(authorization_path)]
    first_code, first = run_cli(args, local_root=local_root)
    second_code, second = run_cli(args, local_root=local_root)
    assert first_code == second_code == 0
    assert first["appended"] is True
    assert second["appended"] is False


def test_case_path_escape_fails(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    outside = tmp_path / "case.json"
    outside.write_text("{}", encoding="utf-8")
    code, result = run_cli(["analyze", "--case", str(outside)], local_root=local_root)
    assert code == 2
    assert result["issues"] == [{"code": "PATH_ESCAPE_FORBIDDEN"}]


def test_generated_cli_outputs_pass_language_policies(tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    case_path = _local_case(local_root)
    for action in ("analyze", "compare"):
        code, result = run_cli([action, "--case", str(case_path)], local_root=local_root)
        assert code == 0
        output = json.dumps(result, sort_keys=True)
        assert scan_text(output, policy="domain", suffix=".json") == []
        assert scan_text(output, policy="advice", suffix=".json") == []
