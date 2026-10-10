"""Runtime content policy definitions and deterministic scanners."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .containment import contains_private_segment


# This module is the runtime policy definition and is the sole runtime exemption.
_DOMAIN_TERMS = (
    "student", "learner", "parent", "mastery", "curriculum", "assessment",
    "pedagogy", "practice plan", "learning receipt", "parent report",
    "student profile", "UnCommon Core", "UCC",
)
_ADVICE_TERMS = (
    "guaranteed", "risk-free", "cannot lose", "sure thing", "this will happen with certainty",
    "the stock will go up",
    "the stock will go down", "trade executed", "order placed", "brokerage connected",
    "we bought", "we sold", "we execute trades for you", "fiduciary guarantee",
    "guaranteed profit",
)
_TEXT_SUFFIXES = {".json", ".md", ".py", ".txt", ".yaml", ".yml"}
_PRIVATE_SURFACES = {"local"}
_DOMAIN_SCOPE = (
    Path("README.md"), Path("SOUL.md"), Path("schemas"), Path("vendor"), Path("adapters"),
    Path("fixtures/valid"), Path("outputs"), Path("reports"), Path("dist"),
)
_ADVICE_SCOPE = (
    Path("README.md"), Path("SOUL.md"),
    Path("vendor/capital-decision-lab/capital_decision_lab/reporting"),
    Path("vendor/capital-decision-lab/capital_decision_lab/plugin"),
    Path("outputs"), Path("reports"), Path("dist"),
)


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)


def _issue(code: str, match: str, path: Path | None = None) -> dict:
    result = {"code": code, "match": match}
    if path is not None:
        result["path"] = str(path)
    return result


def scan_text(text: str, *, policy: str = "domain", suffix: str = "") -> list[dict]:
    """Scan text with stable issue codes and token-aware matching."""
    if policy not in {"domain", "advice"}:
        raise ValueError("SCAN_POLICY_UNKNOWN")
    issues: list[dict] = []
    if policy == "domain":
        reference = re.compile(
            r"(?:\bfrom\s+|\bimport\s+)?(?:ucc)(?:[./\\_-][A-Za-z0-9_.\\/-]+)",
            re.IGNORECASE,
        )
        issues.extend(
            _issue("DOMAIN_REFERENCE_FORBIDDEN", match.group(0))
            for match in reference.finditer(text)
        )
    terms = _DOMAIN_TERMS if policy == "domain" else _ADVICE_TERMS
    code = "DOMAIN_VOCABULARY_FORBIDDEN" if policy == "domain" else "ADVICE_LANGUAGE_FORBIDDEN"
    for term in terms:
        issues.extend(_issue(code, match.group(0)) for match in _term_pattern(term).finditer(text))
    return issues


def boundary_language_scanner(text: str) -> list[dict]:
    """Scan guarantees, certainty, fake execution, and fake account access claims."""
    return scan_text(text, policy="advice")


def _is_marked_adversarial(path: Path) -> bool:
    if path.suffix.casefold() != ".json":
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(value, dict) and value.get("fixture_class") == "adversarial"


def _is_adversarial_fixture_path(path: Path) -> bool:
    parts = [part.casefold() for part in path.parts]
    return any(
        parts[index : index + 2] == ["fixtures", "adversarial"]
        for index in range(max(0, len(parts) - 1))
    )


def scan_path(
    path: Path, *, policy: str = "domain", include_adversarial: bool = False,
    repository_root: Path | None = None,
) -> list[dict]:
    """Scan one file, enforcing private-path and adversarial-fixture rules."""
    candidate = Path(path)
    private_check = Path(candidate.name)
    if repository_root is not None:
        try:
            private_check = candidate.resolve().relative_to(Path(repository_root).resolve())
        except ValueError:
            return [{"code": "PATH_ESCAPE_FORBIDDEN", "path": str(candidate)}]
    elif len(candidate.parents) > 0:
        private_check = Path(candidate.parents[0].name) / candidate.name
    if contains_private_segment(private_check):
        return [{"code": "PRIVATE_PATH_FORBIDDEN", "path": str(candidate)}]
    if not candidate.is_file() or candidate.suffix.casefold() not in _TEXT_SUFFIXES:
        return []
    if (
        _is_adversarial_fixture_path(candidate)
        and _is_marked_adversarial(candidate)
        and not include_adversarial
    ):
        return []
    try:
        text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [{"code": "SCAN_TEXT_UNREADABLE", "path": str(candidate)}]
    return [
        {**issue, "path": str(candidate)}
        for issue in scan_text(text, policy=policy, suffix=candidate.suffix)
    ]


def _policy_exempt(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    normalized = relative.as_posix().casefold()
    runtime_policy = "vendor/capital-decision-lab/capital_decision_lab/privacy/scanner.py"
    return (
        normalized == "readme.md"
        or normalized == runtime_policy
        or normalized.endswith(f"/{runtime_policy}")
        or normalized == "tests/distribution/forbidden_vocabulary.json"
        or normalized.startswith("tests/")
    )


def scan_repository(root: Path, *, policy: str = "domain") -> list[dict]:
    """Scan the approved repository surfaces; policy definitions stay isolated."""
    base = Path(root).resolve(strict=True)
    scopes = _DOMAIN_SCOPE if policy == "domain" else _ADVICE_SCOPE
    issues: list[dict] = []
    for relative in scopes:
        target = base / relative
        candidates = [target] if target.is_file() else sorted(target.rglob("*")) if target.is_dir() else []
        for candidate in candidates:
            if candidate.is_file() and not _policy_exempt(candidate, base):
                relative_candidate = candidate.relative_to(base)
                if contains_private_segment(relative_candidate):
                    issues.append({"code": "PRIVATE_PATH_FORBIDDEN", "path": str(candidate)})
                    continue
                if _is_adversarial_fixture_path(candidate) and _is_marked_adversarial(candidate):
                    continue
                if candidate.suffix.casefold() not in _TEXT_SUFFIXES:
                    continue
                try:
                    text = candidate.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    issues.append({"code": "SCAN_TEXT_UNREADABLE", "path": str(candidate)})
                    continue
                issues.extend(
                    {**issue, "path": str(candidate)}
                    for issue in scan_text(text, policy=policy, suffix=candidate.suffix)
                )
    return issues
