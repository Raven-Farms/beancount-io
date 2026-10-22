"""A remembered rules path that became a pipe is dropped, not opened (w5/893).

Recall validated the remembered rules by reading them, and reading a named
pipe nobody feeds waits forever, before any warning or explicit replacement
could be used.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RULES = '[[rule]]\nmatch = "Grocer"\naccount = "Expenses:Food"\n'


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "--json", "--no-input", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,  # a hang fails here instead of stalling the suite
    )


@pytest.fixture
def remembered(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n'
        "2024-01-01 open Expenses:Food USD\n2024-01-01 open Expenses:Uncategorized USD\n"
    )
    (tmp_path / "bank.csv").write_text("Date,Description,Amount\n2024-02-01,Grocer,-10\n")
    (tmp_path / "rules.toml").write_text(RULES)
    (tmp_path / "alternate.toml").write_text(RULES)
    saved = _bea(tmp_path, "import", "bank.csv", "--csv", "auto", "--account", "Assets:Cash", "--rules", "rules.toml")
    assert saved.returncode == 0, saved.stderr
    (tmp_path / "rules.toml").unlink()
    os.mkfifo(tmp_path / "rules.toml")
    return tmp_path


@pytest.mark.skipif(sys.platform == "win32", reason="named pipes are POSIX here")
def test_a_recalled_pipe_is_warned_about_and_dropped(remembered: Path) -> None:
    result = _bea(remembered, "import", "bank.csv")

    assert result.returncode == 0, result.stderr
    notes = " ".join(json.loads(result.stdout)["data"]["notes"])
    assert "Remembered --rules" in notes and "is a pipe, not a file" in notes and "importing without rules" in notes


@pytest.mark.skipif(sys.platform == "win32", reason="named pipes are POSIX here")
def test_an_explicit_replacement_is_still_used(remembered: Path) -> None:
    result = _bea(remembered, "import", "bank.csv", "--rules", "alternate.toml")

    assert result.returncode == 0, result.stderr
    (row,) = json.loads(result.stdout)["data"]["rows"]
    assert "Expenses:Food" in row["accounts"]


@pytest.mark.skipif(sys.platform == "win32", reason="named pipes are POSIX here")
def test_an_explicit_pipe_is_still_refused(remembered: Path) -> None:
    result = _bea(
        remembered, "import", "bank.csv", "--csv", "auto", "--account", "Assets:Cash", "--rules", "rules.toml"
    )

    assert result.returncode == 2, result.stderr
