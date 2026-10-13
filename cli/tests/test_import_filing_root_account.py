"""An importer whose `account()` is a filing root imports rows posted under it (w5/223).

Beangulp defines `account()` as the account a document is filed under, so a
brokerage importer returns `Assets:Broker` and posts to `Assets:Broker:Cash`
and `Assets:Broker:HOOL`. Import matched the name exactly and refused the
whole batch with "has no posting to its source account".
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
2026-01-01 open Assets:Broker:Cash USD
2026-01-01 open Assets:Broker:HOOL HOOL
2026-01-01 open Income:Broker:Dividends USD
2026-01-01 open Equity:Opening

2026-01-02 * "Opening balance"
  Assets:Broker:Cash  5000.00 USD
  Equity:Opening
"""

IMPORTER = """\
import datetime
from decimal import Decimal as D
from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.position import Cost


class Broker:
    name = "broker"

    def __init__(self, filed, root="Assets:Broker"):
        self.filed, self.root = filed, root

    def identify(self, filepath):
        return filepath.endswith(".txt")

    def account(self, filepath):
        return self.filed

    def extract(self, filepath, existing):
        day = datetime.date(2026, 1, 5)
        return [
            self.row(filepath, 1, day, "Buy 10 HOOL", [
                self.leg(f"{self.root}:HOOL", "10", "HOOL", Cost(D("100.00"), "USD", day, None)),
                self.leg(f"{self.root}:Cash", "-1000.00", "USD"),
            ]),
            self.row(filepath, 2, datetime.date(2026, 1, 20), "Dividend HOOL", [
                self.leg(f"{self.root}:Cash", "12.50", "USD"),
                self.leg("Income:Broker:Dividends", "-12.50", "USD"),
            ]),
        ]

    @staticmethod
    def row(filepath, line, day, narration, legs):
        meta = data.new_metadata(filepath, line)
        return data.Transaction(meta, day, "*", "Broker", narration, frozenset(), frozenset(), legs)

    @staticmethod
    def leg(account, number, currency, cost=None):
        return data.Posting(account, Amount(D(number), currency), cost, None, None, None)


CONFIG = [Broker(FILED)]
"""


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "stmt.txt").write_text("statement\n")
    return ledger


def _import(book: Path, filed: str, *args: str) -> Any:
    config = book.parent / "imp.py"
    config.write_text(IMPORTER.replace("FILED", repr(filed)))
    return runner.invoke(
        app,
        [
            "--json",
            "--no-input",
            "--file",
            str(book),
            "import",
            str(book.parent / "stmt.txt"),
            "--config",
            str(config),
            *args,
        ],
    )


def _statuses(result: Any) -> list[str]:
    return [row["status"] for row in json.loads(result.stdout)["data"]["rows"]]


def test_rows_posted_under_the_filing_root_preview_apply_and_deduplicate(book: Path) -> None:
    preview = _import(book, "Assets:Broker")
    assert preview.exit_code == 0, preview.output
    data = json.loads(preview.stdout)["data"]
    assert data["account"] == "Assets:Broker" and data["ready"] == 2
    assert [row["amount"] for row in data["rows"]] == ["10 HOOL, -1000.00 USD", "12.50 USD"]

    applied = _import(book, "Assets:Broker", "--apply")
    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.stdout)["data"]["written"] == 2
    text = book.read_text()
    assert "Buy 10 HOOL" in text and "Dividend HOOL" in text
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0

    again = _import(book, "Assets:Broker", "--apply")
    assert again.exit_code == 0, again.output
    assert _statuses(again) == ["duplicate", "duplicate"]
    assert book.read_text() == text


def test_an_exact_source_account_is_matched_as_before(book: Path) -> None:
    """The note's control: `account()` names the posting account itself."""
    applied = _import(book, "Assets:Broker:Cash", "--apply")
    assert applied.exit_code == 0, applied.output
    data = json.loads(applied.stdout)["data"]
    assert data["written"] == 2
    assert [row["amount"] for row in data["rows"]] == ["-1000.00 USD", "12.50 USD"]
    assert _statuses(_import(book, "Assets:Broker:Cash", "--apply")) == ["duplicate", "duplicate"]


@pytest.mark.parametrize("filed", ["Assets:Checking", "Assets:Bro"], ids=["unrelated", "name-prefix-only"])
def test_a_row_outside_the_source_account_is_refused_with_a_remedy(book: Path, filed: str) -> None:
    before = book.read_text()

    refused = _import(book, filed, "--apply")

    assert refused.exit_code == 1
    message = json.loads(refused.stderr)["error"]["message"]
    assert f"Importer row 1 has no posting to its source account {filed} or to an account under it" in message
    assert "it posts to Assets:Broker:HOOL, Assets:Broker:Cash." in message
    assert "account() must return an account the row posts to, or a parent of one." in message
    assert book.read_text() == before
