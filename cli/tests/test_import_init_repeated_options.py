"""`import` and `init` refuse two different values for one option, as `add` does (w5/311).

Click keeps the last value of a repeated scalar option: a second `--account`
booked the rows to that account with exit 0 and remembered it, a second
`--csv` or `--rules` silently dropped the first, and `init -c USD -c EUR`
wrote EUR alone.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Wallet BTC
2026-01-01 open Equity:Opening
2026-01-01 open Expenses:Uncategorized
"""
MAPPING = "date=Date,amount=Amount,payee=Payee"


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
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_text("Date,Amount,Payee\n2026-01-05,-3.00,Cafe\n")
    for name in ("r1.toml", "r2.toml"):
        (tmp_path / name).write_text('[[rule]]\nmatch = "cafe"\naccount = "Expenses:Uncategorized"\n')
    return tmp_path


@pytest.mark.parametrize(
    ("options", "named"),
    [
        (["--csv", MAPPING, "--account", "Assets:Checking", "--account", "Assets:Wallet"], "--account"),
        (["--csv", "date=Date,amount=Amount", "--csv", "payee=Payee", "--account", "Assets:Checking"], "--csv"),
        (["--csv", MAPPING, "--account", "Assets:Checking", "--rules", "r1.toml", "--rules", "r2.toml"], "--rules"),
    ],
)
@pytest.mark.parametrize("apply", [False, True], ids=["preview", "apply"])
def test_import_refuses_two_values(books: Path, options: list[str], named: str, apply: bool) -> None:
    result = _bea(books, "-f", "main.bean", "import", "s.csv", *options, *(["--apply"] if apply else []))
    assert result.returncode == 2, result.stdout + result.stderr
    assert f"Conflicting values for one option: {named} " in " ".join(result.stderr.split())
    assert (books / "main.bean").read_text() == LEDGER
    assert not list((books / "config").rglob("*import*"))


def test_import_accepts_the_same_value_twice(books: Path) -> None:
    result = _bea(
        books,
        "-f",
        "main.bean",
        "import",
        "s.csv",
        "--csv",
        MAPPING,
        "--account",
        "Assets:Checking",
        "--account",
        "Assets:Checking",
    )
    assert result.returncode == 0, result.stderr


def test_init_refuses_two_currencies(books: Path) -> None:
    result = _bea(books, "init", "i2", "-c", "USD", "-c", "EUR", "--date", "2026-01-01")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "-c 'USD' and -c 'EUR'" in result.stderr
    assert not (books / "i2").exists()
