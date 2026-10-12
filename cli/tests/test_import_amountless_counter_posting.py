"""A Python importer may leave the counter-posting's amount for Beancount to infer (w5/074).

The blocked-row check read `units.currency` on every posting, so a row whose
categorized leg had no amount crashed the import with a raw `AttributeError`
whenever that leg's account was unopened or restricted its currencies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
option "operating_currency" "USD"

2026-01-01 open Assets:Checking USD
2026-01-01 open Liabilities:Card USD
2026-01-01 open Expenses:Food
2026-01-01 open Equity:Opening

2026-01-02 * "Opening balance"
  Assets:Checking  1000.00 USD
  Equity:Opening
"""

IMPORTER = """\
import csv, datetime
from decimal import Decimal
from beancount.core.amount import Amount
from beancount.core.data import Posting, Transaction, new_metadata


class Elided:
    name = "elided"

    def identify(self, filepath):
        return filepath.endswith(".csv")

    def account(self, filepath):
        return "Assets:Checking"

    def extract(self, filepath, existing):
        out = []
        with open(filepath, newline="") as stream:
            for line, row in enumerate(csv.DictReader(stream), start=2):
                postings = [
                    Posting("Assets:Checking", Amount(Decimal(row["Amount"]), "USD"), None, None, None, None),
                    Posting(row["Cat"], None, None, None, None, None),
                ]
                if row.get("Extra"):
                    postings.insert(
                        1, Posting("Expenses:Food", Amount(Decimal(row["Extra"]), "EUR"), None, None, None, None)
                    )
                out.append(
                    Transaction(
                        new_metadata(filepath, line),
                        datetime.date.fromisoformat(row["Date"]),
                        "*", None, row["Desc"], frozenset(), frozenset(), postings,
                    )
                )
        return out


CONFIG = [Elided()]
"""


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "imp.py").write_text(IMPORTER)
    return ledger


def _import(book: Path, category: str, *args: str, extra: str = "") -> Any:
    source = book.parent / "row.csv"
    source.write_text(f"Date,Desc,Amount,Cat,Extra\n2026-01-05,Pay card,-12.00,{category},{extra}\n")
    return runner.invoke(
        app,
        [
            "--json",
            "--no-input",
            "--file",
            str(book),
            "import",
            str(source),
            "--config",
            str(book.parent / "imp.py"),
            *args,
        ],
    )


@pytest.mark.parametrize("category", ["Liabilities:Card", "Expenses:Food"], ids=["restricted", "unrestricted"])
def test_an_amountless_leg_on_an_open_account_previews_and_applies(book: Path, category: str) -> None:
    preview = _import(book, category)
    applied = _import(book, category, "--apply")

    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.stdout)["data"]["ready"] == 1
    assert applied.exit_code == 0, applied.output
    assert category in book.read_text().split("Pay card")[1]
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_an_amountless_leg_on_an_unopened_account_is_blocked_with_a_working_remedy(book: Path) -> None:
    before = book.read_text()

    blocked = _import(book, "Expenses:Dining", "--apply")

    assert blocked.exit_code != 0
    assert "AttributeError" not in blocked.output
    remedy = "bea add open --account Expenses:Dining --date 2026-01-05 -c USD"
    assert remedy in blocked.output
    assert book.read_text() == before
    opened = runner.invoke(app, ["--file", str(book), *remedy.split()[1:]])
    assert opened.exit_code == 0, opened.output
    applied = _import(book, "Expenses:Dining", "--apply")
    assert applied.exit_code == 0, applied.output
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_an_ambiguous_amountless_leg_is_left_to_validation(book: Path) -> None:
    """Two weight currencies: the inferred leg's currency is unknowable before booking."""
    before = book.read_text()

    restricted = _import(book, "Liabilities:Card", "--apply", extra="3.00")
    unopened = _import(book, "Expenses:Dining", extra="3.00")

    for result in (restricted, unopened):
        assert "AttributeError" not in result.output
    error = json.loads(restricted.stderr)["error"]
    assert restricted.exit_code == 1 and error["category"] == "validation"
    assert any("Invalid currency EUR for account 'Liabilities:Card'" in line for line in error["details"])
    assert book.read_text() == before
    reason = json.loads(unopened.stdout)["data"]["rows"][0]["reason"]
    assert reason.endswith("Run: bea add open --account Expenses:Dining --date 2026-01-05.")
