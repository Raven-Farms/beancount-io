"""A YYYY-MM-DD date that names no real day says so, not "Use YYYY-MM-DD format" (w5/330)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n'


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("args", "value"),
    [
        (
            (
                "-f",
                "main.bean",
                "add",
                "transaction",
                "X",
                "--date",
                "2027-02-29",
                "-p",
                "Expenses:Food 1 USD",
                "-p",
                "Assets:Checking",
            ),
            "2027-02-29",
        ),
        (("init", "ib", "--currency", "USD", "--date", "2026-02-30"), "2026-02-30"),
        (("-f", "main.bean", "list", "transaction", "--from-date", "2026-04-31"), "2026-04-31"),
    ],
    ids=["add", "init", "list"],
)
def test_a_nonexistent_day_is_named(tmp_path: Path, args: tuple[str, ...], value: str) -> None:
    result = _bea(tmp_path, *args)
    assert result.returncode == 2
    assert f"Invalid date '{value}': not a calendar date" in result.stderr
    assert "Use YYYY-MM-DD format" not in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_a_badly_shaped_date_keeps_the_format_hint(tmp_path: Path) -> None:
    result = _bea(tmp_path, "-f", "main.bean", "list", "transaction", "--from-date", "2027-2-28")
    assert result.returncode == 2
    assert "Invalid date '2027-2-28'. Use YYYY-MM-DD format." in result.stderr
