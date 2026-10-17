"""`--id-key FITID` matches `fitid`, and a key no entry can carry is refused (w5/469).

Any typed key replaced the default list, so `FITID` (how OFX spells it) or an
empty key turned native-ID matching off: a reused bank ID with changed data
was written with exit 0 beside the entry it already named.
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
2026-01-01 open Expenses:Uncategorized USD

2026-02-01 * "COFFEE"
  fitid: "F1"
  Assets:Checking          -4.50 USD
  Expenses:Uncategorized    4.50 USD
"""
IMPORTER = """import csv, datetime
from decimal import Decimal
from beancount.core import amount, data


class Bank:
    name = "bank"

    def identify(self, filepath):
        return filepath.endswith(".csv")

    def account(self, filepath):
        return "Assets:Checking"

    def extract(self, filepath, existing):
        out = []
        with open(filepath) as handle:
            for index, row in enumerate(csv.DictReader(handle), start=2):
                meta = data.new_metadata(filepath, index)
                meta["fitid"] = row["Ref"]
                number = Decimal(row["Amount"])
                day = datetime.date.fromisoformat(row["Date"])
                postings = [
                    data.Posting("Assets:Checking", amount.Amount(number, "USD"), None, None, None, None),
                    data.Posting("Expenses:Uncategorized", amount.Amount(-number, "USD"), None, None, None, None),
                ]
                narration = row["Description"]
                out.append(data.Transaction(meta, day, "*", None, narration, frozenset(), frozenset(), postings))
        return out


CONFIG = [Bank()]
"""


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "s.csv").write_text("Date,Description,Amount,Ref\n2026-02-01,COFFEE,-9.99,F1\n")
    return tmp_path


def _import(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "import", "s.csv", "--apply", *args],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("key", ["fitid", "FITID", "Fitid"])
def test_a_default_key_in_any_case_keeps_the_conflict(books: Path, key: str) -> None:
    result = _import(books, "--id-key", key)

    assert result.returncode == 4, result.stdout + result.stderr
    assert "Row 1 (conflict): Stable ID matches an entry with different transaction data." in result.stderr
    assert (books / "main.bean").read_text() == LEDGER


@pytest.mark.parametrize("key", ["", "Ref", "9id"])
def test_a_key_no_entry_can_carry_is_refused(books: Path, key: str) -> None:
    result = _import(books, "--id-key", key)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"--id-key {key!r} is not a metadata key" in result.stderr
    assert (books / "main.bean").read_text() == LEDGER
