"""A Fava or forecast overlay that includes a working ledger does not become its root (w5/578).

w5/343/346 sent every write on an included file through the file that
includes it. A `forecast.bean` beside `main.bean` that includes it and adds
projections then took over validation and dedupe for `main.bean` itself: a
wrong balance was written, a right one refused, and a real bank row skipped as
a duplicate of a forecast entry. A file is a leaf only when its includer
defines what it reads (an account opened, a plugin, an option).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Rent USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "Opening"
  Assets:Checking  5000.00 USD
  Equity:Opening
"""
FORECAST = '2026-02-01 # "Landlord" "Rent (forecast)"\n  Expenses:Rent  1000.00 USD\n  Assets:Checking\n'


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "forecast.bean").write_text('include "main.bean"\n' + FORECAST)
    return tmp_path


def _bea(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(cwd / ".config"),
        XDG_CACHE_HOME=str(cwd / ".cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _balance(amount: str) -> list[str]:
    return ["add", "balance", "-a", "Assets:Checking", "--amount", amount, "--date", "2026-03-01"]


def test_a_balance_is_judged_against_the_ledger_itself(books: Path) -> None:
    wrong = _bea(books, *_balance("4000.00 USD"))
    right = _bea(books, *_balance("5000.00 USD"))
    check = _bea(books, "check")

    assert wrong.returncode == 1 and "expected 4000.00 USD != accumulated 5000.00 USD" in wrong.stderr, wrong.stderr
    assert right.returncode == 0, right.stderr
    assert "is included by" not in right.stderr
    assert check.returncode == 0, check.stdout + check.stderr


def test_a_bank_row_is_not_a_duplicate_of_a_forecast_entry(books: Path) -> None:
    (books / "bank.csv").write_text("Date,Amount,Payee\n2026-02-01,-1000.00,Landlord\n")
    (books / "rules.toml").write_text('[[rule]]\nmatch = "Landlord"\naccount = "Expenses:Rent"\n')

    result = _bea(
        books,
        "--json",
        "import",
        "bank.csv",
        "--csv",
        "date=Date,amount=Amount,payee=Payee",
        "--account",
        "Assets:Checking",
        "--rules",
        "rules.toml",
        "--apply",
        "--duplicates",
        "skip",
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["data"]
    assert data["written"] == 1 and [row["status"] for row in data["rows"]] == ["new"]
    assert "Landlord" in (books / "main.bean").read_text()


def test_a_failing_read_is_not_sent_to_the_overlay(books: Path) -> None:
    (books / "main.bean").write_text(MAIN + "2026-03-01 balance Assets:Checking 1.00 USD\n")

    check = _bea(books, "check")

    assert check.returncode == 1
    assert "Balance failed" in check.stdout + check.stderr
    assert "forecast.bean" not in check.stdout + check.stderr


def test_a_title_only_overlay_in_the_parent_folder_is_no_root(tmp_path: Path) -> None:
    (tmp_path / "books").mkdir()
    (tmp_path / "books" / "main.bean").write_text(MAIN)
    (tmp_path / "fava.bean").write_text('option "title" "Fava"\ninclude "books/main.bean"\n' + FORECAST)

    result = _bea(tmp_path / "books", *_balance("5000.00 USD"))

    assert result.returncode == 0, result.stderr
    assert "is included by" not in result.stderr
