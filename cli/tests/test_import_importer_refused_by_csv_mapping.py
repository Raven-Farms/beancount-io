"""`--importer` is refused when the column mapping runs the import (w5/240).

The mirror of w5/131: `bea import bank.csv --csv … --account … --importer
NoSuchImporter --apply` accepted the name, dropped it, and wrote the row with
exit 0, while the same unknown name under `--config` was refused.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from cli.main import app

runner = CliRunner()

CONFIG = Path(__file__).resolve().parents[1] / "docs/examples/csv_importers.py"
LEDGER = (
    'option "operating_currency" "USD"\n'
    "2024-01-01 open Assets:Checking USD\n"
    "2024-01-01 open Expenses:Uncategorized USD\n"
    "2024-01-01 open Equity:Opening USD\n"
    '2024-01-02 * "Opening"\n'
    "  Assets:Checking  1000.00 USD\n"
    "  Equity:Opening\n"
)
EXPORT = "Date,Payee,Narration,Amount\n2024-06-02,Cafe,Coffee,-5.25\n"
MAPPING = "date=Date,amount=Amount,payee=Payee,narration=Narration"


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    books = tmp_path / "books"
    books.mkdir()
    ledger = books / "main.bean"
    ledger.write_text(LEDGER)
    (books / "bank.csv").write_text(EXPORT)
    return ledger


def _import(book: Path, *args: str, json_output: bool = False) -> Result:
    source = str(book.parent / "bank.csv")
    lead = ["--json"] if json_output else []
    return runner.invoke(app, [*lead, "--no-input", "--file", str(book), "import", source, *args])


def test_an_explicit_mapping_refuses_the_importer_name_and_writes_nothing(book: Path) -> None:
    result = _import(book, "--csv", MAPPING, "--account", "Assets:Checking", "--importer", "NoSuchImporter", "--apply")

    assert result.exit_code == 2, result.output
    assert "--importer selects a Python importer by name" in result.stderr
    assert "the --csv column mapping" in result.stderr
    assert "--config FILE" in result.stderr
    assert result.stdout == ""
    assert book.read_text() == LEDGER


def test_an_inferred_mapping_refuses_it_in_json(book: Path) -> None:
    result = _import(book, "--account", "Assets:Checking", "--importer", "NoSuchImporter", json_output=True)

    assert result.exit_code == 2, result.output
    message = json.loads(result.stderr)["error"]["message"]
    assert message.startswith("--importer selects a Python importer by name")
    assert "read from its header row" in message
    assert result.stdout == ""
    assert book.read_text() == LEDGER


def test_a_remembered_mapping_refuses_it(book: Path) -> None:
    saved = _import(book, "--csv", MAPPING, "--account", "Assets:Checking", json_output=True)
    assert saved.exit_code == 0, saved.output

    result = _import(book, "--importer", "NoSuchImporter", "--apply")

    assert result.exit_code == 2, result.output
    assert "--importer selects a Python importer by name" in result.stderr
    assert "remembered for its header row" in result.stderr
    assert book.read_text() == LEDGER


def test_the_mapping_still_imports_without_the_importer_name(book: Path) -> None:
    result = _import(book, "--csv", MAPPING, "--account", "Assets:Checking", "--apply")

    assert result.exit_code == 0, result.output
    assert "csv → Assets:Checking" in result.stdout
    assert '"Cafe" "Coffee"' in book.read_text()


def test_a_python_config_still_resolves_the_importer_name(book: Path) -> None:
    unknown = _import(book, "--config", str(CONFIG), "--importer", "NoSuchImporter")
    assert unknown.exit_code == 2, unknown.output
    assert "No importer named 'NoSuchImporter'; available: categorized-checking." in unknown.stderr

    # The bundled importer recognizes its own export layout, not the bare one.
    (book.parent / "bank.csv").write_text(
        "Date,Payee,Narration,Amount,Currency,Category\n2024-06-02,Cafe,Coffee,-5.25,USD,Expenses:Uncategorized\n"
    )
    known = _import(book, "--config", str(CONFIG), "--importer", "categorized-checking", json_output=True)
    assert known.exit_code == 0, known.output
    assert json.loads(known.stdout)["data"]["importer"] == "categorized-checking"
    assert book.read_text() == LEDGER
