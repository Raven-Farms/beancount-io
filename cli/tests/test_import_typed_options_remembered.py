"""An option typed on a recalled preview is what the flag-free `--apply` replays (w5/073).

Once a mapping was remembered, `--date-format` or `--rules` typed on a later
preview changed that preview but was never saved, so the documented flag-free
`--apply` recomputed without it and wrote rows nobody had reviewed.
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
    "2026-01-01 open Expenses:Food\n"
    "2026-01-01 open Expenses:Fees\n"
    "2026-01-01 open Expenses:Uncategorized\n"
)
AMBIGUOUS = "Date,Description,Amount\n05/01/2026,Lunch,-20.00\n06/02/2026,Train,-40.00\n"


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _import(book: Path, source: Path, *args: str, ok: bool = True) -> Any:
    result = runner.invoke(app, ["--json", "--no-input", "--file", str(book), "import", str(source), *args])
    if ok:
        assert result.exit_code == 0, result.output
        return json.loads(result.stdout)["data"]
    return result


def test_a_date_format_typed_on_a_recalled_preview_is_what_apply_writes(book: Path) -> None:
    source = book.parent / "a.csv"
    source.write_text(AMBIGUOUS)
    first = _import(book, source, "--account", "Assets:Checking")
    assert "2026-05-01" in first["diff"]

    reviewed = _import(book, source, "--date-format", "%d/%m/%Y")
    applied = _import(book, source, "--apply")

    assert "2026-01-05" in reviewed["diff"] and "2026-02-06" in reviewed["diff"]
    assert any("Updated remembered settings" in note and "%d/%m/%Y" in note for note in reviewed["notes"])
    assert applied["remembered"]["date_format"] == "%d/%m/%Y"
    assert any("--date-format %d/%m/%Y" in note for note in applied["notes"])
    text = book.read_text()
    assert '2026-01-05 ! "Lunch"' in text and '2026-02-06 ! "Train"' in text
    assert "2026-05-01" not in text and "2026-06-02" not in text


def test_rules_and_default_account_typed_on_a_recalled_preview_are_replayed(book: Path) -> None:
    source = book.parent / "a.csv"
    source.write_text("Date,Description,Amount\n2026-03-01,Lunch,-20.00\n2026-03-02,Bank fee,-1.00\n")
    rules = book.parent / "rules.toml"
    rules.write_text('[[rule]]\nmatch = "Lunch"\naccount = "Expenses:Food"\n')
    _import(book, source, "--account", "Assets:Checking")

    reviewed = _import(book, source, "--rules", str(rules), "--default-account", "Expenses:Fees")
    applied = _import(book, source, "--apply")

    assert "Expenses:Food" in reviewed["diff"] and "Expenses:Fees" in reviewed["diff"]
    assert applied["remembered"]["rules"] == str(rules.resolve())
    assert applied["remembered"]["default_account"] == "Expenses:Fees"
    text = book.read_text()
    assert "Expenses:Food" in text.split("Lunch")[1]
    assert "Expenses:Fees" in text.split("Bank fee")[1]
    assert "Expenses:Uncategorized" not in text.split("Lunch")[1]


def test_a_delimiter_typed_on_a_recalled_preview_is_replayed(book: Path) -> None:
    source = book.parent / "a.csv"
    source.write_text("Date;Description;Amount\n2026-03-01;Lunch;-20.00\n")
    _import(book, source, "--account", "Assets:Checking")

    _import(book, source, "--delimiter", ";")
    applied = _import(book, source, "--apply")

    assert applied["remembered"]["delimiter"] == ";"
    assert '2026-03-01 ! "Lunch"' in book.read_text()


def test_a_failed_recalled_run_leaves_the_remembered_settings_alone(book: Path, bea_config_dir: Path) -> None:
    source = book.parent / "a.csv"
    source.write_text(AMBIGUOUS)
    _import(book, source, "--account", "Assets:Checking")
    (record,) = (bea_config_dir / "importers").glob("csv-*.json")
    before = record.read_bytes()

    failed = _import(book, source, "--date-format", "%Y-%m-%d", ok=False)

    assert failed.exit_code != 0
    assert record.read_bytes() == before
    assert "Updated remembered settings" not in failed.output


def test_an_unchanged_typed_option_says_nothing(book: Path) -> None:
    source = book.parent / "a.csv"
    source.write_text(AMBIGUOUS)
    _import(book, source, "--account", "Assets:Checking", "--date-format", "%d/%m/%Y")

    again = _import(book, source, "--date-format", "%d/%m/%Y")

    assert not any("Updated remembered settings" in note for note in again["notes"])
