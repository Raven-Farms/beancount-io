"""A balance dated before an account's existing open names that open, not `bea add open` (w5/345).

The hint was written for never-opened accounts; for one opened later, or on
the assertion's own day, following "bea add open" was refused as a duplicate.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n2026-03-01 open Assets:Bank USD\n2026-01-01 open Equity:OpeningBalances USD\n'
)


def _balance(tmp_path: Path, account: str, date: str) -> str:
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
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "-f",
            "main.bean",
            "add",
            "balance",
            "--date",
            date,
            "--account",
            account,
            "--amount",
            "50 USD",
        ],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 1
    assert (tmp_path / "main.bean").read_text() == LEDGER
    return " ".join(result.stderr.split())


@pytest.mark.parametrize("date", ["2026-02-15", "2026-03-01"], ids=["before-open", "same-day"])
def test_an_existing_open_is_named(tmp_path: Path, date: str) -> None:
    message = _balance(tmp_path, "Assets:Bank", date)
    assert f"Assets:Bank opens 2026-03-01 at {tmp_path / 'main.bean'}:2, not before this {date} assertion." in message
    assert "bea add open" not in message


def test_a_never_opened_account_keeps_the_add_open_hint(tmp_path: Path) -> None:
    message = _balance(tmp_path, "Assets:Never", "2026-02-15")
    assert "Assets:Never must be open on an earlier day before this balance assertion (bea add open" in message
