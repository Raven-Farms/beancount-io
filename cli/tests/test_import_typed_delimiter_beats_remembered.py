"""A typed `--delimiter` wins over a separator bea read for an earlier file (w5/266).

A flag-free import of a `;` file used to store the echoed `delimiter=';'`
inside the remembered mapping. A later comma file with the same header then
had its typed `--delimiter ','` refused as disagreeing with a `--csv
delimiter=` the user never passed.
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
    "2026-01-01 open Assets:Euro EUR\n"
    "2026-01-01 open Expenses:Uncategorized\n"
)
SEMICOLON = "Date;Description;Amount\n2026-08-02;Coffee;-4,50\n"
COMMA = "Date,Description,Amount\n2026-09-02,Lunch,-9.00\n"
MAPPING = "date=Date,amount=Amount,narration=Description"


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


def test_a_typed_delimiter_reads_a_comma_file_after_an_inferred_semicolon_import(book: Path) -> None:
    first = _data(_import(book, "aug.csv", SEMICOLON, "--account", "Assets:Checking", "--apply"))
    assert first["written"] == 1

    second = _data(_import(book, "sep.csv", COMMA, "--delimiter", ","))

    assert second["ready"] == 1
    assert (second["rows"][0]["date"], second["rows"][0]["amount"]) == ("2026-09-02", "-9.00 USD")
    assert second["config_source"] == "remembered --csv"
    assert second["remembered"]["delimiter"] == ","


def test_an_inferred_separator_is_not_stored_in_the_remembered_mapping(book: Path, bea_config_dir: Path) -> None:
    _data(_import(book, "aug.csv", SEMICOLON, "--account", "Assets:Checking", "--apply"))

    (record,) = (bea_config_dir / "importers").glob("csv-*.json")
    (stored,) = json.loads(record.read_text())["sources"]

    assert stored["mapping"] == MAPPING
    assert stored["delimiter"] is None


def test_a_record_that_kept_the_echoed_key_does_not_refuse_a_typed_delimiter(book: Path, bea_config_dir: Path) -> None:
    """Records written before w5/077 carry `delimiter=';'` inside the mapping."""
    _data(_import(book, "aug.csv", SEMICOLON, "--account", "Assets:Checking", "--apply"))
    (record,) = (bea_config_dir / "importers").glob("csv-*.json")
    stored = json.loads(record.read_text())
    stored["sources"][0]["mapping"] = f"{MAPPING},delimiter=';'"
    record.write_text(json.dumps(stored))

    second = _data(_import(book, "sep.csv", COMMA, "--delimiter", ","))

    assert second["ready"] == 1
    assert second["rows"][0]["amount"] == "-9.00 USD"


def test_a_fresh_config_reads_the_comma_file_with_the_typed_delimiter(book: Path) -> None:
    control = _data(_import(book, "sep.csv", COMMA, "--delimiter", ",", "--account", "Assets:Checking"))

    assert control["ready"] == 1
    assert control["config_source"] != "remembered --csv"


def test_a_delimiter_typed_both_ways_is_still_refused_when_the_two_disagree(book: Path) -> None:
    result = _import(
        book, "sep.csv", COMMA, "--csv", f"{MAPPING},delimiter=';'", "--delimiter", ",", "--account", "Assets:Checking"
    )

    assert result.exit_code == 2
    assert "--delimiter ',' disagrees with --csv delimiter=';'" in result.output
