"""`bea treeify` refuses a bad input path in one line with the documented exit (w5/352).

A missing path or a directory exited 1 (`validation`) and an unreadable file
was not exit 3, each behind upstream's `FileNotFoundError`/`IsADirectoryError`/
`PermissionError` class name.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _treeify(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "treeify", *args],
        env=env,
        cwd=tmp_path,
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize(
    ("name", "code", "said"),
    [("nope.txt", 2, "does not exist"), ("d", 2, "is a directory"), ("ro.txt", 3, "permission denied")],
)
def test_a_bad_input_is_named_with_its_exit(tmp_path: Path, name: str, code: int, said: str) -> None:
    if name == "ro.txt" and (sys.platform == "win32" or os.geteuid() == 0):
        pytest.skip("POSIX permissions that root ignores")
    (tmp_path / "d").mkdir()
    (tmp_path / "ro.txt").write_text("x\n")
    (tmp_path / "ro.txt").chmod(0o000)
    try:
        result = _treeify(tmp_path, name)
    finally:
        (tmp_path / "ro.txt").chmod(0o600)
    assert result.returncode == code, result.stderr
    assert said in result.stderr and f"'{name}'" in result.stderr
    for name_of_class in ("FileNotFoundError", "IsADirectoryError", "PermissionError"):
        assert name_of_class not in result.stderr


def test_a_file_and_stdin_still_render(tmp_path: Path) -> None:
    (tmp_path / "ok.txt").write_text("Assets:Cash 5\n")
    assert "Cash 5" in _treeify(tmp_path, "ok.txt").stdout
    assert "Cash 5" in _treeify(tmp_path, stdin="Assets:Cash 5\n").stdout
