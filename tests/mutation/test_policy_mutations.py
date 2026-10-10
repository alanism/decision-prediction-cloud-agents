from __future__ import annotations

import importlib.util
from pathlib import Path

from capital_decision_lab.privacy.scanner import scan_repository


ROOT = Path(__file__).resolve().parents[2]


def _builder():
    path = ROOT / "scripts" / "build_profile_staging.py"
    spec = importlib.util.spec_from_file_location("build_profile_staging_mutation", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mutation_private_directory_added_to_allowlist_is_killed(tmp_path: Path) -> None:
    module = _builder()
    private = ROOT / "local" / "mutation-sentinel.json"
    private.write_text('{"private_sentinel":"mutation"}', encoding="utf-8")
    module._ALLOWED_DIRS = (*module._ALLOWED_DIRS, Path("local"))
    try:
        result = module.build_staging(ROOT, tmp_path / "profile")
        assert result["success"] is False
        assert result["issues"] == [{"code": "STAGING_PATH_FORBIDDEN"}]
    finally:
        private.unlink(missing_ok=True)


def test_mutation_domain_term_in_valid_schema_is_killed(tmp_path: Path) -> None:
    schema = tmp_path / "schemas" / "mutated.schema.json"
    schema.parent.mkdir()
    schema.write_text('{"title":"Student profile"}', encoding="utf-8")
    issues = scan_repository(tmp_path, policy="domain")
    assert any(item["code"] == "DOMAIN_VOCABULARY_FORBIDDEN" for item in issues)


def test_mutation_domain_namespace_in_runtime_python_is_killed(tmp_path: Path) -> None:
    runtime = tmp_path / "plugins" / "probe" / "module.py"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("from ucc.contracts import receipt\n", encoding="utf-8")
    issues = scan_repository(tmp_path, policy="domain")
    assert any(item["code"] == "DOMAIN_REFERENCE_FORBIDDEN" for item in issues)


def test_mutation_advice_language_in_generated_report_is_killed(tmp_path: Path) -> None:
    report = tmp_path / "reports" / "result.md"
    report.parent.mkdir()
    report.write_text("This is a guaranteed buy signal.", encoding="utf-8")
    issues = scan_repository(tmp_path, policy="advice")
    assert any(item["code"] == "ADVICE_LANGUAGE_FORBIDDEN" for item in issues)


def test_adversarial_marker_cannot_exempt_a_valid_schema(tmp_path: Path) -> None:
    schema = tmp_path / "schemas" / "mutated.schema.json"
    schema.parent.mkdir()
    schema.write_text(
        '{"fixture_class":"adversarial","title":"Student profile"}',
        encoding="utf-8",
    )
    issues = scan_repository(tmp_path, policy="domain")
    assert any(item["code"] == "DOMAIN_VOCABULARY_FORBIDDEN" for item in issues)

