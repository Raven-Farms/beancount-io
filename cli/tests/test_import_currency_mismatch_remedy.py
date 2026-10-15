"""A currency-blocked row offers a remedy the run can apply (w5/318).

Every mismatch said "name the row's commodity with --csv currency=CODE": a
Python-importer run refuses `--csv`, and on a rule's category account that
setting relabelled the money and moved the block to the source account.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Bank USD
2026-01-01 open Assets:Euro EUR
2026-01-01 open Expenses:Food USD
2026-01-01 open Expenses:Travel EUR
2026-01-01 open Expenses:Uncategorized
"""
IMPORTER = """\
import datetime
from decimal import Decimal as D
from beancount.core import amount, data


def P(account, number, currency, price=None):
    return data.Posting(account, amount.Amount(D(number), currency), None, price, None, None)


class Imp:
    name = "imp"

    def identify(self, filepath):
        return filepath.endswith("stmt.txt")

    def account(self, filepath):
        return "Assets:Bank"

    def extract(self, filepath, existing):
        meta = data.new_metadata(filepath, 1)
        price = amount.Amount(D("1.10"), "USD")
        postings = [P("Assets:Bank", "-11.00", "USD"), P("Expenses:Food", "10.00", "EUR", price)]
        day = datetime.date(2026, 1, 5)
        return [data.Transaction(meta, day, "*", "Shop", "Paris", frozenset(), frozenset(), postings)]


CONFIG = [Imp()]
"""


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "stmt.txt").write_text("x\n")
    (tmp_path / "imp.py").write_text(IMPORTER)
    (tmp_path / "s.csv").write_text("Date,Payee,Amount,Cur\n2026-01-05,Hotel,-50.00,USD\n")
    (tmp_path / "r.toml").write_text('[[rule]]\nmatch = "hotel"\naccount = "Expenses:Travel"\n')
    return tmp_path


def _reason(books: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--no-input", "-f", "main.bean", "import", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    (row,) = json.loads(result.stdout)["data"]["rows"]
    assert row["status"] == "blocked"
    return str(row["reason"])


def test_a_python_importer_row_is_not_told_to_pass_csv(books: Path) -> None:
    reason = _reason(books, "stmt.txt", "--config", "imp.py")
    assert "--csv" not in reason
    assert "'Expenses:Food'" in reason and "importer posts EUR" in reason


def test_a_rule_account_row_names_the_account_to_change(books: Path) -> None:
    reason = _reason(
        books, "s.csv", "--csv", "date=Date,payee=Payee,amount=Amount", "--account", "Assets:Bank", "--rules", "r.toml"
    )
    assert "currency=" not in reason
    assert "that chose 'Expenses:Travel'" in reason


def test_a_source_account_row_still_offers_the_currency_setting(books: Path) -> None:
    reason = _reason(
        books, "s.csv", "--csv", "date=Date,payee=Payee,amount=Amount,currency=Cur", "--account", "Assets:Euro"
    )
    assert reason.startswith("Cannot post USD to 'Assets:Euro'")
    assert "--csv currency=CODE" in reason
