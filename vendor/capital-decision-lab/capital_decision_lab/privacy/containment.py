"""Canonical path containment with Windows reparse-point protection."""

from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath


_REPARSE_POINT = 0x400


def _is_reparse_point(path: Path) -> bool:
    try:
        stat = path.lstat()
    except OSError:
        return False
    return path.is_symlink() or bool(getattr(stat, "st_file_attributes", 0) & _REPARSE_POINT)


def validate_contained_path(root: Path, candidate: Path) -> dict:
    """Resolve a path and reject escape, symlink, or junction traversal."""
    try:
        resolved_root = Path(root).resolve(strict=True)
    except OSError:
        return {"allowed": False, "issues": [{"code": "CONTAINMENT_ROOT_INVALID"}]}

    raw = Path(candidate)
    # POSIX treats Windows drives and backslashes as relative filename text.
    # Reject foreign absolute/drive-relative syntax before native resolution.
    # On Windows, native containment below handles valid Windows paths.
    if os.name != "nt" and (PureWindowsPath(str(raw)).drive or str(raw).startswith("\\")):
        return {"allowed": False, "issues": [{"code": "PATH_ESCAPE_FORBIDDEN"}]}
    if not raw.is_absolute():
        raw = resolved_root / raw

    current = raw
    existing: list[Path] = []
    while True:
        if current.exists() or current.is_symlink():
            existing.append(current)
        if len(current.parents) == 0:
            break
        ancestor = current.parents[0]
        current = ancestor
    if any(_is_reparse_point(item) for item in existing):
        return {"allowed": False, "issues": [{"code": "REPARSE_POINT_FORBIDDEN"}]}

    try:
        resolved = raw.resolve(strict=False)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError):
        return {"allowed": False, "issues": [{"code": "PATH_ESCAPE_FORBIDDEN"}]}
    return {"allowed": True, "resolved_path": str(resolved), "issues": []}


def contains_private_segment(path: Path) -> bool:
    return any(part.casefold() == "local" for part in Path(path).parts)
