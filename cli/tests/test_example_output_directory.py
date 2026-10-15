"""`bea example -o DIR` gets the directory refusal, with or without --force (w5/353).

An existing directory was treated as a file to overwrite: exit 4 advising
--force, which then met the directory refusal it could never pass.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _example(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "example", "--seed", "3", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("force", [[], ["--force"]], ids=["plain", "force"])
def test_a_directory_is_refused_as_a_directory(tmp_path: Path, force: list[str]) -> None:
    (tmp_path / "d2").mkdir()
    result = _example(tmp_path, "-o", "d2", *force)
    assert result.returncode == 2, result.stderr
    assert "--output must be a file path, not a directory (d2)." in result.stderr
    assert "Pass --force" not in result.stderr


def test_an_existing_file_still_needs_force(tmp_path: Path) -> None:
    (tmp_path / "f.bean").write_text("old\n")
    assert _example(tmp_path, "-o", "f.bean").returncode == 4
    assert _example(tmp_path, "-o", "f.bean", "--force").returncode == 0
    assert (tmp_path / "f.bean").read_text() != "old\n"
