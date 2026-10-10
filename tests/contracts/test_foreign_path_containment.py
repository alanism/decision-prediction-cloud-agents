"""Cross-platform path syntax must not bypass containment intent."""
import os
from pathlib import Path
from capital_decision_lab.privacy.containment import validate_contained_path

def test_windows_path_spellings_are_rejected_on_posix(tmp_path: Path) -> None:
    if os.name == "nt":
        return
    for candidate in ["C:/Windows/System32/cmd.exe", r"C:\Windows\System32\cmd.exe", "C:relative.txt", r"\\server\share\file.txt", "//server/share/file.txt", r"\Windows\file.txt"]:
        result = validate_contained_path(tmp_path, Path(candidate))
        assert result["allowed"] is False, candidate
        assert result["issues"] == [{"code": "PATH_ESCAPE_FORBIDDEN"}], candidate

def test_native_relative_and_absolute_paths_still_work(tmp_path: Path) -> None:
    assert validate_contained_path(tmp_path, Path("nested/input.json"))["allowed"] is True
    assert validate_contained_path(tmp_path, tmp_path / "nested/input.json")["allowed"] is True
    assert validate_contained_path(tmp_path, Path("../escape.json"))["allowed"] is False
