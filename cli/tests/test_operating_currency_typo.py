"""A malformed `option "operating_currency"` is named where it is the fallback (w5/328).

Beancount accepts `"usd"`, so `check` passed and every fallback failed its own
way: `report` asked for `USD → usd` prices, `add` reported a token error and
`import` cited `column None`. w3/427 already named the same typo for `-x`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "{currency}"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food
2026-01-01 open Equity:Opening
2026-01-02 * "Open"
  Assets:Checking  100.00 USD
  Equity:Opening
"""
COMMANDS = {
    "report": ("report", "balance-sheet"),
    "balance": ("balance",),
    "add": ("add", "transaction", "Lunch", "--date", "2026-01-07", "-p", "Expenses:Food 5", "-p", "Assets:Checking"),
    "import": ("import", "s.csv", "--csv", "date=Date,payee=Payee,amount=Amount", "--account", "Expenses:Food"),
}


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "-f", "main.bean", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _books(tmp_path: Path, currency: str) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER.format(currency=currency))
    (tmp_path / "s.csv").write_text("Date,Payee,Amount,Cur\n2026-01-06,Cafe,-3.00,USD\n")
    return tmp_path


@pytest.mark.parametrize("name", sorted(COMMANDS))
def test_a_lowercase_operating_currency_is_named(tmp_path: Path, name: str) -> None:
    books = _books(tmp_path, "usd")
    result = _bea(books, *COMMANDS[name])
    message = " ".join(result.stderr.split())
    assert result.returncode == 2, result.stdout + result.stderr
    assert 'option "operating_currency" "usd" at ' in message and "main.bean:1" in message
    assert "Did you mean 'USD'?" in message
    assert "column None" not in message and "Missing prices" not in message
    assert (books / "main.bean").read_text() == LEDGER.format(currency="usd")


def test_an_explicit_currency_still_works(tmp_path: Path) -> None:
    books = _books(tmp_path, "usd")
    assert _bea(books, "report", "balance-sheet", "-x", "USD").returncode == 0
    mapped = _bea(
        books, *COMMANDS["import"][:3], "date=Date,payee=Payee,amount=Amount,currency=Cur", *COMMANDS["import"][4:]
    )
    assert mapped.returncode == 0, mapped.stderr


@pytest.mark.parametrize("name", sorted(COMMANDS))
def test_a_valid_operating_currency_is_unchanged(tmp_path: Path, name: str) -> None:
    assert _bea(_books(tmp_path, "USD"), *COMMANDS[name]).returncode == 0
