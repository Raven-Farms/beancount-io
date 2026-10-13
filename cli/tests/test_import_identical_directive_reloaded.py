"""Re-running an importer skips the notes, events and balances it already wrote (w5/224).

"Identical directive" compared the importer entry's printed text with the
printed text of the reloaded ledger. The loader reads ledger text as NFC, so
decomposed strings never matched what they had become; and a balance that
currently fails loads with its difference attached, which printed as a
`; Diff:` comment the importer's own balance lacks. Either way every re-run
appended the same directives again and exited 0.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
option "operating_currency" "USD"

2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food
2026-01-01 open Equity:Opening

2026-01-02 * "Opening balance"
  Assets:Checking  1000.00 USD
  Equity:Opening
"""
BALANCE = "2026-01-06 balance Assets:Checking 994.75 USD\n"

IMPORTER = """\
import datetime, unicodedata
from decimal import Decimal as D
from beancount.core import data
from beancount.core.amount import Amount

FORM = "@FORM@"
DIRECTIVES = "@DIRECTIVES@"


class Imp:
    name = "demo"

    def identify(self, filepath):
        return filepath.endswith(".txt")

    def account(self, filepath):
        return "Assets:Checking"

    def extract(self, filepath, existing):
        n = lambda s: unicodedata.normalize(FORM, s)
        m = lambda i: data.new_metadata(filepath, i)
        day = datetime.date(2026, 1, 6)
        units = Amount(D("5.25"), "USD")
        out = [
            data.Transaction(
                m(1), datetime.date(2026, 1, 5), "*", "Cafe", "Coffee", frozenset(), frozenset(),
                [
                    data.Posting("Assets:Checking", -units, None, None, None, None),
                    data.Posting("Expenses:Food", units, None, None, None, None),
                ],
            )
        ]
        if DIRECTIVES == "all":
            out.append(data.Note(m(2), day, "Assets:Checking", n("relev\\u00e9 de janvier"), None, None))
            out.append(data.Event(m(3), day, "location", n("Z\\u00fcrich")))
            meta = dict(m(4), source=n("relev\\u00e9"))
        else:
            meta = m(4)
        out.append(data.Balance(meta, day, "Assets:Checking", Amount(D("994.75"), "USD"), None, None))
        return out


CONFIG = [Imp()]
"""


def _book(tmp_path: Path, ledger: str, form: str, directives: str) -> Path:
    (tmp_path / "stmt.txt").write_text("statement\n")
    (tmp_path / "imp.py").write_text(IMPORTER.replace("@FORM@", form).replace("@DIRECTIVES@", directives))
    book = tmp_path / "main.bean"
    book.write_text(ledger, encoding="utf-8")
    return book


def _apply(book: Path, *args: str) -> dict[str, Any]:
    argv = ["--json", "--no-input", "--file", str(book), "import", str(book.parent / "stmt.txt")]
    result = runner.invoke(app, [*argv, "--config", str(book.parent / "imp.py"), "--apply", *args])
    assert result.exit_code == 0, result.output
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def _counts(book: Path) -> dict[str, int]:
    text = book.read_text(encoding="utf-8")
    return {kind: text.count(f" {kind} ") for kind in ("note", "event", "balance")} | {"txn": text.count('"Cafe"')}


@pytest.mark.parametrize("form", ["NFD", "NFC"])
def test_rerunning_an_importer_writes_each_directive_once(tmp_path: Path, bea_config_dir: Path, form: str) -> None:
    book = _book(tmp_path, LEDGER, form, "all")

    assert _apply(book)["written"] == 4
    once = book.read_text(encoding="utf-8")
    # What was written is what a reload reads, so the next comparison is exact.
    assert once == unicodedata.normalize("NFC", once)
    assert "relevé de janvier" in once and "Zürich" in once

    for _ in range(2):
        again = _apply(book)
        assert again["written"] == 0
        assert [(row["status"], row["reason"]) for row in again["rows"][1:]] == [
            ("duplicate", "Identical directive already exists.")
        ] * 3

    assert book.read_text(encoding="utf-8") == once
    assert _counts(book) == {"note": 1, "event": 1, "balance": 1, "txn": 1}


def test_a_failing_balance_already_in_the_ledger_is_an_identical_directive(
    tmp_path: Path, bea_config_dir: Path
) -> None:
    # The assertion fails until the coffee is imported, so it loads with a difference.
    book = _book(tmp_path, LEDGER + "\n" + BALANCE, "NFC", "balance")

    applied = _apply(book, "--allow-errors")

    assert applied["written"] == 1
    balance = applied["rows"][1]
    assert (balance["status"], balance["reason"]) == ("duplicate", "Identical directive already exists.")
    assert "Diff" not in balance["entry"]
    assert _counts(book) == {"note": 0, "event": 0, "balance": 1, "txn": 1}


def test_a_balance_the_importer_wrote_is_skipped_on_the_next_run(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path, LEDGER, "NFC", "balance")

    assert _apply(book)["written"] == 2
    assert _apply(book)["written"] == 0

    assert _counts(book) == {"note": 0, "event": 0, "balance": 1, "txn": 1}


def test_a_failing_balance_on_another_date_is_not_identical(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path, LEDGER + "\n" + BALANCE.replace("01-06", "01-03"), "NFC", "balance")

    applied = _apply(book, "--allow-errors")

    assert applied["written"] == 2
    assert applied["rows"][1]["status"] == "new"
    assert _counts(book)["balance"] == 2
