from __future__ import annotations

import json
from pathlib import Path

from capital_decision_lab.plugin.commands import run_cli
from tests.orchestration.test_analyze_position import response, social_fields, workflow_case, write_inputs

ROOT = Path(__file__).resolve().parents[2]


def test_page_method_cli_pack_run(tmp_path: Path) -> None:
    local = tmp_path / "local"
    local.mkdir()
    case_path = local / "page_case.json"
    case_path.write_text(json.dumps(workflow_case()), encoding="utf-8")

    code, run = run_cli(["method", "run", "--pack", "page", "--case", str(case_path)], local_root=local)
    assert code == 0
    assert run["method_result"]["pack_id"] == "page"
    assert run["method_result"]["contract_version"] == "nhi.method_pack_result.v1"


def test_page_analyze_position_method_flag(tmp_path: Path) -> None:
    local = tmp_path / "local"
    local.mkdir()
    case_path = local / "case.json"
    case_path.write_text(json.dumps(workflow_case()), encoding="utf-8")
    folder = local / "host"
    write_inputs(folder, [response("x_twitter", social_fields())])

    code, analyzed = run_cli(["analyze-position", "--case", str(case_path), "--host-inputs", str(folder), "--method", "page"], local_root=local)
    assert code == 0
    assert analyzed["method_result"]["pack_id"] == "page"

