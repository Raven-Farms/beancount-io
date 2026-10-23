"""A possible duplicate's reason names the fields that met on both sides (w5/824).

The reason said "payee" whenever the row had one, so a row with a payee that
met a payee-less ledger entry on their narrations was told "Date, payee and
source amount match". The mirror case, a narration-only row meeting an entry
on its payee, was told "narration", though the entry's narration differs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

HEAD = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n'


@pytest.fixture
def books(tmp_path: Path, bea_config_dir: Path) -> Path:
    return tmp_path


def _reason(books: Path, entry: str, body: str, mapping: str) -> str:
    ledger = books / "main.bean"
    ledger.write_text(HEAD + entry)
    (books / "bank.csv").write_text(body)
    result = CliRunner().invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(books / "bank.csv")]
        + ["--csv", mapping, "--account", "Assets:Checking"],
    )
    assert result.exit_code == 0, result.output
    rows: list[dict[str, Any]] = json.loads(result.stdout)["data"]["rows"]
    (row,) = rows
    assert row["status"] == "possible_duplicate", row
    return str(row["reason"])


def test_a_row_with_a_payee_meeting_a_payee_less_entry_says_narration(books: Path) -> None:
    entry = '2026-09-28 * "CARD PURCHASE 1234"\n  Assets:Checking  -4.50 USD\n  Expenses:Food\n'
    body = "Date,Payee,Description,Amount\n2026-09-28,Starbucks,CARD PURCHASE 1234,-4.50\n"

    reason = _reason(books, entry, body, "date=Date,payee=Payee,narration=Description,amount=Amount")

    assert reason == "Date, narration and source amount match; neither has a bank ID."


def test_a_narration_only_row_meeting_an_entry_payee_names_both_fields(books: Path) -> None:
    entry = '2026-10-04 * "Netflix" "monthly plan"\n  Assets:Checking  -15.49 USD\n  Expenses:Food\n'
    body = "Date,Description,Amount\n10/04/2026,Netflix,-15.49\n"

    reason = _reason(books, entry, body, "date=Date,narration=Description,amount=Amount")

    assert reason == (
        "Date and source amount match the ledger entry, and this row's narration is its payee; neither has a bank ID."
    )


def test_a_row_payee_meeting_an_entry_narration_names_both_fields(books: Path) -> None:
    entry = '2026-09-28 * "Starbucks"\n  Assets:Checking  -4.50 USD\n  Expenses:Food\n'
    body = "Date,Payee,Description,Amount\n2026-09-28,Starbucks,CARD PURCHASE 1234,-4.50\n"

    reason = _reason(books, entry, body, "date=Date,payee=Payee,narration=Description,amount=Amount")

    assert reason == (
        "Date and source amount match the ledger entry, and this row's payee is its narration; neither has a bank ID."
    )


def test_payees_that_meet_still_say_payee(books: Path) -> None:
    entry = '2026-09-28 * "Starbucks" "latte"\n  Assets:Checking  -4.50 USD\n  Expenses:Food\n'
    body = "Date,Payee,Description,Amount\n2026-09-28,Starbucks,CARD PURCHASE 1234,-4.50\n"

    reason = _reason(books, entry, body, "date=Date,payee=Payee,narration=Description,amount=Amount")

    assert reason == "Date, payee and source amount match; neither has a bank ID."
