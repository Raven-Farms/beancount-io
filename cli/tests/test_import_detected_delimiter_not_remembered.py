"""A detected CSV separator belongs to the file it was read from (w5/077).

It was stored with the remembered mapping and forced onto the next export
sharing the header, so a re-save with another separator was refused for
lacking a column it plainly had.
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
    'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Uncategorized\n'
)
COMMA = "Date,Description,Amount\n2026-01-05,Coffee,-3.00\n"
SEMICOLON = "Date;Description;Amount\n2026-02-05;Tea;-2,50\n"
TAB = "Date\tDescription\tAmount\n2026-03-05\tJuice\t-4.00\n"


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _import(book: Path, name: str, text: str, *args: str) -> Any:
    source = book.parent / name
    source.write_text(text)
    return runner.invoke(app, ["--json", "--no-input", "--file", str(book), "import", str(source), *args])


def _data(result: Any) -> Any:
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


@pytest.mark.parametrize(
    ("text", "date", "amount"), [(SEMICOLON, "2026-02-05", "-2.50 USD"), (TAB, "2026-03-05", "-4.00 USD")]
)
def test_a_resaved_export_is_read_with_its_own_separator(book: Path, text: str, date: str, amount: str) -> None:
    first = _data(_import(book, "jan.csv", COMMA, "--account", "Assets:Checking", "--apply"))
    assert first["written"] == 1

    second = _data(_import(book, "feb.csv", text))

    assert second["ready"] == 1
    assert (second["rows"][0]["date"], second["rows"][0]["amount"]) == (date, amount)
    assert second["config_source"] == "remembered --csv"
    assert second["remembered"]["delimiter"] is None
    assert not any("--delimiter" in note for note in second["notes"])


@pytest.mark.parametrize("how", ["flag", "csv-key"])
def test_a_delimiter_the_user_passed_is_remembered_and_named(book: Path, how: str) -> None:
    mapping = "date=Date,amount=Amount,narration=Description"
    chosen = ["--delimiter", ";"] if how == "flag" else []
    spec = mapping if how == "flag" else f"{mapping},delimiter=';'"
    _data(_import(book, "feb.csv", SEMICOLON, "--csv", spec, "--account", "Assets:Checking", *chosen))

    again = _data(_import(book, "feb.csv", SEMICOLON))

    assert again["remembered"]["delimiter"] == ";"
    assert any("--delimiter ';'" in note for note in again["notes"])
    assert again["ready"] == 1


def test_a_remembered_delimiter_that_does_not_read_the_file_gives_way_to_detection(book: Path) -> None:
    _data(_import(book, "feb.csv", SEMICOLON, "--account", "Assets:Checking", "--delimiter", ";"))

    comma = _data(_import(book, "jan.csv", COMMA))

    assert comma["ready"] == 1 and comma["rows"][0]["date"] == "2026-01-05"
    assert comma["remembered"]["delimiter"] is None
    assert any("does not read jan.csv" in note for note in comma["notes"])


def test_a_record_that_kept_a_detected_separator_no_longer_forces_it(book: Path, bea_config_dir: Path) -> None:
    """Records written before this fix carry the detected separator."""
    _data(_import(book, "jan.csv", COMMA, "--account", "Assets:Checking"))
    (record,) = (bea_config_dir / "importers").glob("csv-*.json")
    stored = json.loads(record.read_text())
    stored["sources"][0]["delimiter"] = ","
    record.write_text(json.dumps(stored))

    second = _data(_import(book, "feb.csv", SEMICOLON))

    assert second["ready"] == 1 and second["rows"][0]["amount"] == "-2.50 USD"
