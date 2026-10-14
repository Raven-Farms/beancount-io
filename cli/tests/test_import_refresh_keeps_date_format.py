"""An explicit `--csv` refresh never erases a remembered `--date-format` unannounced (w5/267).

A day-first export imported with `--date-format %d/%m/%Y`, then refreshed by
an explicit `--csv` without the flag on a file whose dates happened to read
the same way, lost the remembered format without a word. The next flag-free
import of a file with only low day numbers was booked month-first.
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
HEADER = "Date,Description,Amount\n"
EXPLICIT = ("--csv", "date=Date,amount=Amount,narration=Description", "--account", "Assets:Checking")
DAY_FIRST = "%d/%m/%Y"


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "aug.csv").write_text(HEADER + "02/08/2026,Coffee,-4.50\n03/08/2026,Tea,-2.00\n")
    (tmp_path / "sep.csv").write_text(HEADER + "13/09/2026,Lunch,-9.00\n")
    (tmp_path / "oct.csv").write_text(HEADER + "04/10/2026,Bus,-2.50\n")
    seeded = _import(ledger, "aug.csv", *EXPLICIT, "--date-format", DAY_FIRST, "--apply")
    assert seeded["written"] == 2
    return ledger


def _import(book: Path, name: str, *args: str) -> Any:
    result = runner.invoke(app, ["--json", "--no-input", "--file", str(book), "import", str(book.parent / name), *args])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


def _remembered(config: Path) -> Any:
    (record,) = (config / "importers").glob("csv-*.json")
    (entry,) = json.loads(record.read_text())["sources"]
    return entry["date_format"]


def test_a_refresh_on_a_file_that_agrees_keeps_the_remembered_format(book: Path, bea_config_dir: Path) -> None:
    refreshed = _import(book, "sep.csv", *EXPLICIT, "--apply")

    assert not any("Discarded remembered" in note for note in refreshed["notes"])
    assert _remembered(bea_config_dir) == DAY_FIRST

    october = _import(book, "oct.csv", "--apply")

    assert october["date_format"] == DAY_FIRST
    assert any(f"--date-format {DAY_FIRST}" in note for note in october["notes"])
    text = book.read_text()
    assert '2026-10-04 ! "Bus"' in text
    assert "2026-04-10" not in text
    assert '2026-08-02 ! "Coffee"' in text and '2026-09-13 ! "Lunch"' in text


def test_a_preview_refresh_keeps_it_too(book: Path, bea_config_dir: Path) -> None:
    _import(book, "sep.csv", *EXPLICIT)

    assert _remembered(bea_config_dir) == DAY_FIRST
    assert _import(book, "oct.csv")["rows"][0]["entry"].startswith("2026-10-04")


def test_a_refresh_on_a_file_that_reads_otherwise_still_names_the_discard(book: Path, bea_config_dir: Path) -> None:
    refreshed = _import(book, "oct.csv", *EXPLICIT)

    (discard,) = [note for note in refreshed["notes"] if "Discarded remembered" in note]
    assert f"--date-format {DAY_FIRST}" in discard
    assert _remembered(bea_config_dir) is None


def test_a_typed_format_still_replaces_the_remembered_one(book: Path, bea_config_dir: Path) -> None:
    _import(book, "oct.csv", *EXPLICIT, "--date-format", "%m/%d/%Y")

    assert _remembered(bea_config_dir) == "%m/%d/%Y"
