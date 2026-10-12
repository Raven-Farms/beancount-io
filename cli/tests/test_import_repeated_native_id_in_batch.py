"""A native bank ID that repeats inside one export never silently drops a row (w5/075).

Header inference adopts a `Reference Number` column as the stable ID. A
monthly autopay reuses that reference with the same amount, so the second row
was classed an exact duplicate, dropped with exit 0, and explained with a
reason that was false: nothing in the ledger carried the ID before the run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Expenses:Uncategorized\n"
    "2026-01-01 open Equity:Opening\n\n"
    '2026-01-02 * "Opening balance"\n  Assets:Checking  1000.00 USD\n  Equity:Opening\n'
)
HEADER = "Date,Description,Amount,Reference Number\n"
RENT = HEADER + "2026-01-01,Rent January,-1200.00,RENT-AUTOPAY\n2026-02-01,Rent February,-1200.00,RENT-AUTOPAY\n"
BALANCE = "SELECT sum(position) AS total WHERE account = 'Assets:Checking'"


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _import(book: Path, text: str, *args: str) -> Any:
    source = book.parent / "rent.csv"
    source.write_text(text)
    return runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(book), "import", str(source), "--account", "Assets:Checking", *args],
    )


def _balance(book: Path) -> str:
    result = runner.invoke(app, ["--file", str(book), "query", BALANCE])
    assert result.exit_code == 0, result.output
    return result.output


def test_a_repeated_reference_with_another_date_needs_review_and_names_the_earlier_row(book: Path) -> None:
    preview = _import(book, RENT)
    applied = _import(book, RENT, "--apply")

    assert preview.exit_code == 0, preview.output
    rows = json.loads(preview.stdout)["data"]["rows"]
    assert [row["status"] for row in rows] == ["new", "possible_duplicate"]
    assert "repeats row 1 of this import" in rows[1]["reason"]
    assert "already in the ledger" not in rows[1]["reason"]
    assert rows[1]["match"]["row"] == 1
    assert applied.exit_code == 4, applied.output
    assert book.read_text() == LEDGER


def test_including_the_repeat_writes_both_rows_and_a_reimport_skips_them(book: Path) -> None:
    applied = _import(book, RENT, "--apply", "--duplicates", "include")

    assert applied.exit_code == 0, applied.output
    assert "-1400.00 USD" in _balance(book)
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0
    again = _import(book, RENT, "--apply", "--duplicates", "include")
    assert again.exit_code == 0, again.output
    data = json.loads(again.stdout)["data"]
    assert [row["status"] for row in data["rows"]] == ["duplicate", "duplicate"]
    assert all("already in the ledger" in row["reason"] for row in data["rows"])
    assert "-1400.00 USD" in _balance(book)


def test_skipping_the_repeat_is_an_explicit_choice(book: Path) -> None:
    applied = _import(book, RENT, "--apply", "--duplicates", "skip")

    assert applied.exit_code == 0, applied.output
    assert "-200.00 USD" in _balance(book)


@pytest.mark.parametrize("second", ["Rent January", "Rent (January)"], ids=["identical", "tidier-description"])
def test_a_same_day_repeat_names_the_import_not_the_ledger(book: Path, second: str) -> None:
    twice = HEADER + f"2026-01-01,Rent January,-1200.00,RENT-AUTOPAY\n2026-01-01,{second},-1200.00,RENT-AUTOPAY\n"

    preview = _import(book, twice)

    rows = json.loads(preview.stdout)["data"]["rows"]
    assert [row["status"] for row in rows] == ["new", "duplicate"]
    assert rows[1]["reason"] == "Repeats row 1 of this import."


def test_a_repeated_reference_with_another_amount_is_still_a_conflict(book: Path) -> None:
    changed = HEADER + "2026-01-01,Rent January,-1200.00,RENT-AUTOPAY\n2026-02-01,Rent February,-1250.00,RENT-AUTOPAY\n"

    preview = _import(book, changed)

    rows = json.loads(preview.stdout)["data"]["rows"]
    assert rows[1]["status"] == "conflict"
    assert "repeats row 1 of this import with different transaction data" in rows[1]["reason"]
