"""`init` maps uncreatable paths to usage errors naming the blocker (w5/795).

A symlink loop, an illegal byte and an overlong component each exited 1
with a raw `OSError` (and the illegal byte leaked the staging name).
They are bad arguments: exit 2, naming the link or name, with nothing
written. A full disk keeps its ledger error (w5/610).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink and name semantics")


def _bea(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(cwd / "config"),
        XDG_CACHE_HOME=str(cwd / "cache"),
        XDG_DATA_HOME=str(cwd / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _clean(result: subprocess.CompletedProcess[str]) -> str:
    text = " ".join((result.stdout + result.stderr).split())
    for raw in ("Errno", "OSError", "Traceback", ".bea-"):
        assert raw not in text, text
    assert "Nothing was written" in text
    return text


def _tree(work: Path) -> list[str]:
    return sorted(
        str(path.relative_to(work))
        for path in work.rglob("*")
        if {"config", "cache"}.isdisjoint(path.relative_to(work).parts)
    )


def test_symlink_loop_is_a_usage_error_naming_the_link(tmp_path: Path) -> None:
    (tmp_path / "loop").symlink_to("loop")
    before = _tree(tmp_path)

    result = _bea(tmp_path, "init", "loop/books", "--currency", "USD", "--date", "2026-01-01")

    assert result.returncode == 2, result.stdout + result.stderr
    text = _clean(result)
    assert "is a symbolic-link loop" in text
    assert str(tmp_path / "loop") in text
    assert _tree(tmp_path) == before


@pytest.mark.skipif(sys.platform != "darwin", reason="only some filesystems reject non-UTF-8 names")
def test_illegal_byte_is_a_usage_error_without_a_staging_leak(tmp_path: Path) -> None:
    before = _tree(tmp_path)

    result = _bea(tmp_path, "init", "bad\udcff/books", "--currency", "USD", "--date", "2026-01-01")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "is not a valid file name" in _clean(result)
    assert _tree(tmp_path) == before


def test_overlong_name_is_a_usage_error_naming_the_component(tmp_path: Path) -> None:
    long = "n" * 300
    before = _tree(tmp_path)

    result = _bea(tmp_path, "init", f"{long}/books", "--currency", "USD", "--date", "2026-01-01")

    assert result.returncode == 2, result.stdout + result.stderr
    text = _clean(result)
    assert "exceeds the filesystem's name limit" in text
    assert long in text
    assert _tree(tmp_path) == before
