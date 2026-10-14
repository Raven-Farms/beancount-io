"""A directory walk stops on a subdirectory or file it may not read (w5/274).

`Path.rglob` swallowed the error from a directory it could not list, so
`bea format --check DIR` exited 0 for a subtree it never opened.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORMATTED = "2026-01-01 open Assets:A USD\n"
UNFORMATTED = """2026-01-01 open Assets:B USD
2026-01-02 * "x"
  Assets:B     1 USD
  Assets:B  -1 USD
"""
MODES = ["--check", "--dry-run", "-i"]

pytestmark = pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() == 0, reason="needs POSIX permissions that bind the caller"
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Iterator[Path]:
    root = tmp_path / "books" / "t"
    locked = root / "locked"
    locked.mkdir(parents=True)
    (root / "a.bean").write_text(FORMATTED)
    (locked / "z.bean").write_text(UNFORMATTED)
    yield root
    # Whatever a test locked must be removable again by pytest's tmp_path cleanup.
    locked.chmod(0o755)
    (locked / "z.bean").chmod(0o644)


def test_the_readable_tree_reports_the_unformatted_file(tree: Path) -> None:
    result = _bea(tree.parent, "format", "--check", str(tree))
    assert result.returncode == 1
    assert f"would format: {tree / 'locked' / 'z.bean'}" in result.stdout + result.stderr


@pytest.mark.parametrize("mode", MODES)
def test_an_unlistable_subdirectory_stops_the_walk_and_is_named(tree: Path, mode: str) -> None:
    locked = tree / "locked"
    locked.chmod(0)
    result = _bea(tree.parent, "format", mode, str(tree))
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert f"Could not read {locked}: Permission denied" in result.stderr
    assert "formatted" not in result.stdout
    locked.chmod(0o755)
    assert (locked / "z.bean").read_text() == UNFORMATTED
    assert (tree / "a.bean").read_text() == FORMATTED


@pytest.mark.parametrize("mode", MODES)
def test_an_unreadable_walked_file_stops_the_walk_and_is_named(tree: Path, mode: str) -> None:
    target = tree / "locked" / "z.bean"
    target.chmod(0)
    result = _bea(tree.parent, "format", mode, str(tree))
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert f"Could not read {target}: Permission denied" in result.stderr
    target.chmod(0o644)
    assert target.read_text() == UNFORMATTED


def test_json_callers_get_a_usage_error_naming_the_directory(tree: Path) -> None:
    locked = tree / "locked"
    locked.chmod(0)
    result = _bea(tree.parent, "--json", "format", "--check", str(tree))
    assert result.returncode == 2
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert str(locked) in error["message"]


def test_a_directory_symlink_is_still_not_followed(tree: Path) -> None:
    # `rglob` never descended through a directory link; the walk that replaced it must not either.
    (tree / "locked" / "z.bean").write_text(FORMATTED)
    outside = tree.parent / "outside"
    outside.mkdir()
    (outside / "o.bean").write_text(UNFORMATTED)
    (tree / "link").symlink_to(outside, target_is_directory=True)
    result = _bea(tree.parent, "--json", "format", "--check", str(tree))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["scanned"] == 2
