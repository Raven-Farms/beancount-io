"""A bank id matches only rows of the account that issued it (w5/598).

The index of written entries took every entry with a leg on `--account`, so
checking's transfer to savings, carrying checking's `1001`, deduped savings'
own `1001`, a different deposit, as an exact duplicate with exit 0. With an
OFX importer, a shared FITID was a false conflict (exit 4). The result
depended on import order. A hit through a transfer's counter leg is now at
most a possible duplicate: same amount, within a week.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Savings USD
2026-01-01 open Expenses:Groceries USD
2026-01-01 open Expenses:Uncategorized USD
2026-01-01 open Income:Salary USD
2026-01-01 open Income:Interest USD
"""
CHECKING = (
    "Date,Description,Amount,ID\n"
    "2026-09-05,ONLINE TRANSFER TO SAVINGS,-500.00,1001\n"
    "2026-09-06,WHOLE FOODS,-45.00,1002\n"
)
SAVINGS = "Date,Description,Amount,ID\n2026-09-20,MOBILE DEPOSIT,500.00,1001\n2026-09-30,INTEREST PAID,1.25,1002\n"
RULES = {
    "Assets:Checking": '[[rule]]\nmatch = "transfer to savings"\naccount = "Assets:Savings"\n'
    '[[rule]]\nmatch = "whole foods"\naccount = "Expenses:Groceries"\n',
    "Assets:Savings": '[[rule]]\nmatch = "interest"\naccount = "Income:Interest"\n'
    '[[rule]]\nmatch = "deposit"\naccount = "Income:Salary"\n'
    '[[rule]]\nmatch = "from checking"\naccount = "Assets:Checking"\n',
}
MAPPING = "date=Date,amount=Amount,narration=Description,id=ID"
IMPORTER = """\
import datetime
import json
import os
from decimal import Decimal
from beancount.core import amount, data


class Bank:
    name = "bank"

    def identify(self, filepath):
        return filepath.endswith(".ofx")

    def account(self, filepath):
        return os.environ["TEST_ACCOUNT"]

    def extract(self, filepath, existing):
        entries = []
        for line, (day, fitid, narration, legs) in enumerate(json.loads(os.environ["TEST_ROWS"]), 1):
            meta = data.new_metadata(filepath, line)
            meta["fitid"] = fitid
            postings = [
                data.Posting(name, amount.Amount(Decimal(number), "USD"), None, None, None, None)
                for name, number in legs
            ]
            entries.append(data.Transaction(meta, datetime.date.fromisoformat(day), "*", None, narration,
                                            frozenset(), frozenset(), postings))
        return entries


CONFIG = [Bank()]
"""


def _bea(books: Path, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        **extra,
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--no-input", "-f", str(books / "main.bean"), *args],
        cwd=books,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        check=False,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "checking.csv").write_text(CHECKING)
    (tmp_path / "savings.csv").write_text(SAVINGS)
    for account, rules in RULES.items():
        (tmp_path / f"{account.rsplit(':', 1)[1].lower()}.toml").write_text(rules)
    (tmp_path / "imp.py").write_text(IMPORTER)
    (tmp_path / "statement.ofx").write_text("statement\n")
    return tmp_path


def _rows(result: subprocess.CompletedProcess[str]) -> list[dict[str, Any]]:
    payload = json.loads(result.stdout or result.stderr)
    data = payload["data"] if "data" in payload else payload["error"]["result"]
    return list(data["rows"])


def _csv(books: Path, account: str, *flags: str) -> subprocess.CompletedProcess[str]:
    name = account.rsplit(":", 1)[1].lower()
    return _bea(
        books, "import", f"{name}.csv", "--csv", MAPPING, "--account", account, "--rules", f"{name}.toml", *flags
    )


def _savings_balance(books: Path) -> str:
    result = _bea(books, "query", "SELECT sum(number) AS total WHERE account = 'Assets:Savings'")
    assert result.returncode == 0, result.stderr
    return str(json.loads(result.stdout)["data"]["rows"][0][0])


@pytest.mark.parametrize("order", [["Assets:Checking", "Assets:Savings"], ["Assets:Savings", "Assets:Checking"]])
def test_each_accounts_bank_ids_stay_its_own_in_either_order(books: Path, order: list[str]) -> None:
    for account in order:
        result = _csv(books, account, "--apply")
        assert result.returncode == 0, result.stderr
        assert [row["status"] for row in _rows(result)] == ["new", "new"]

    assert _savings_balance(books) == "1001.25"


def test_a_shared_reference_on_both_legs_is_left_for_review(books: Path) -> None:
    """Some banks give both sides of one transfer the same reference: that hit is kept, for review."""
    assert _csv(books, "Assets:Checking", "--apply").returncode == 0
    (books / "savings.csv").write_text("Date,Description,Amount,ID\n2026-09-06,TRANSFER FROM CHECKING,500.00,1001\n")

    review = _csv(books, "Assets:Savings", "--apply")
    skipped = _csv(books, "Assets:Savings", "--apply", "--duplicates", "skip")

    assert review.returncode == 4, review.stderr
    (row,) = _rows(review)
    assert row["status"] == "possible_duplicate"
    assert "on the other side of a transfer from Assets:Checking dated 1 day earlier" in row["reason"]
    assert skipped.returncode == 0, skipped.stderr
    assert _savings_balance(books) == "500.00"


def _ofx(books: Path, account: str, rows: list[Any], *flags: str) -> subprocess.CompletedProcess[str]:
    return _bea(
        books,
        "import",
        "statement.ofx",
        "--config",
        "imp.py",
        *flags,
        TEST_ACCOUNT=account,
        TEST_ROWS=json.dumps(rows),
    )


def test_a_fitid_another_account_issued_is_no_conflict(books: Path) -> None:
    transfer = ["2026-09-05", "1", "Transfer", [["Assets:Checking", "-500"], ["Assets:Savings", "500"]]]
    interest = ["2026-09-30", "1", "Interest", [["Assets:Savings", "1.25"], ["Income:Interest", "-1.25"]]]
    assert _ofx(books, "Assets:Checking", [transfer], "--apply").returncode == 0

    result = _ofx(books, "Assets:Savings", [interest], "--apply")

    assert result.returncode == 0, result.stderr
    assert [row["status"] for row in _rows(result)] == ["new"]
    assert _savings_balance(books) == "501.25"


def test_an_importer_that_lists_the_category_first_still_dedupes_its_own_rows(books: Path) -> None:
    coffee = ["2026-09-07", "7", "Coffee", [["Expenses:Groceries", "5"], ["Assets:Checking", "-5"]]]
    assert _ofx(books, "Assets:Checking", [coffee], "--apply").returncode == 0
    written = (books / "main.bean").read_bytes()

    again = _ofx(books, "Assets:Checking", [coffee], "--apply")

    assert again.returncode == 0, again.stderr
    assert [row["status"] for row in _rows(again)] == ["duplicate"]
    assert (books / "main.bean").read_bytes() == written
