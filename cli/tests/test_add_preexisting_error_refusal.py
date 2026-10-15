"""A write that adds nothing wrong to an already-broken ledger points at `--allow-errors` (w5/396).

The refusal said "The change would leave the ledger invalid" with the advice
for a new balance assertion and no flag, while `add price` and `add balance`
borrowed the read commands' "report anyway".
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Assets:Bank USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "Seed"
  Assets:Cash  100 USD
  Equity:Opening
2026-01-03 balance Assets:Cash 999 USD
"""
COMMANDS = {
    "transaction": ("transaction", "X", "--date", "2026-01-05", "-p", "Expenses:Food 5 USD", "-p", "Assets:Cash"),
    "note": ("note", "--date", "2026-01-05", "-a", "Assets:Cash", "-m", "hi"),
    "price": ("price", "--date", "2026-01-05", "-c", "EUR", "--amount", "1.1 USD"),
    "balance": ("balance", "--date", "2026-01-06", "-a", "Assets:Bank", "--amount", "0 USD"),
}


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("name", list(COMMANDS))
def test_write_on_a_broken_ledger_names_the_flag(tmp_path: Path, name: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    before = ledger.read_bytes()
    result = _bea(tmp_path, "-f", str(ledger), "add", *COMMANDS[name])

    assert result.returncode == 1, result.stderr
    assert ledger.read_bytes() == before
    flat = " ".join(result.stderr.split())
    assert "The ledger already has 1 error(s); nothing was written. Pass --allow-errors to write anyway." in flat
    assert f"{ledger}:9: Balance failed for 'Assets:Cash'" in flat
    assert "leave the ledger invalid" not in flat
    assert "report anyway" not in flat
    assert "start of the day" not in flat
    assert "fees" not in flat


@pytest.mark.parametrize("name", list(COMMANDS))
def test_with_the_flag_the_write_lands(tmp_path: Path, name: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    result = _bea(tmp_path, "-f", str(ledger), "add", *COMMANDS[name], "--allow-errors")

    assert result.returncode == 0, result.stderr
    assert len(ledger.read_text()) > len(LEDGER)


def test_an_error_the_write_adds_is_still_the_change(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    result = _bea(
        tmp_path,
        "-f",
        str(ledger),
        "add",
        "transaction",
        "X",
        "--date",
        "2026-01-05",
        "-p",
        "Expenses:Nope 5 USD",
        "-p",
        "Assets:Cash",
    )

    assert result.returncode == 1, result.stderr
    flat = " ".join(result.stderr.split())
    assert "The change would leave the ledger invalid; nothing was written." in flat
    assert "already has" not in flat
