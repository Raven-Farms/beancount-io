"""A repeated global `--file` with two different ledgers is refused (w5/485).

Click kept the last value for the root group's options, so
`bea -f main.bean -f other.bean add …` wrote to `other.bean` with exit 0,
though every command's own options refuse two values.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Expenses:Food USD\n2026-01-01 open Assets:Cash USD\n'
ADD = ("add", "transaction", "X", "--date", "2026-01-05", "-p", "Expenses:Food 1 USD", "-p", "Assets:Cash")


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    for name in ("main.bean", "other.bean"):
        if not (tmp_path / name).exists():
            (tmp_path / name).write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    "files", [("-f", "main.bean", "-f", "other.bean"), ("--file=main.bean", "--file", "other.bean")]
)
def test_two_ledgers_are_refused_and_nothing_is_written(tmp_path: Path, files: tuple[str, ...]) -> None:
    result = _bea(tmp_path, "--json", *files, *ADD)

    assert result.returncode == 2, result.stdout + result.stderr
    error = json.loads(result.stdout or result.stderr)["error"]
    assert error["message"].startswith("Conflicting values for one option:")
    assert "'main.bean'" in error["message"] and "'other.bean'" in error["message"]
    assert (tmp_path / "main.bean").read_text() == LEDGER
    assert (tmp_path / "other.bean").read_text() == LEDGER


def test_the_same_ledger_twice_still_works(tmp_path: Path) -> None:
    result = _bea(tmp_path, "-f", "main.bean", "--file", "main.bean", *ADD)

    assert result.returncode == 0, result.stderr
    assert "2026-01-05" in (tmp_path / "main.bean").read_text()
