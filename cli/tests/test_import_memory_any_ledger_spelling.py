"""Import settings are remembered per root ledger, not per spelling of its path (w5/205).

The memory was keyed by the resolved path as typed. On a case- and
normalization-insensitive volume `-f Books/main.bean` and `-f books/main.bean`
are one file, so an import through one spelling left a flag-free import through
the other failing as if nothing had been remembered.
"""

from __future__ import annotations

import hashlib
import os
import unicodedata
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from cli.main import app

runner = CliRunner()

CONFIG = Path(__file__).resolve().parents[1] / "docs/examples/csv_importers.py"
LEDGER = (
    'option "operating_currency" "USD"\n'
    "2024-01-01 open Assets:Bank USD\n"
    "2024-01-01 open Assets:Checking USD\n"
    "2024-01-01 open Expenses:Food\n"
    "2024-01-01 open Expenses:Uncategorized USD\n"
)
FIRST = "When,What,Howmuch\n2024-01-02,abc,-5.00\n"
SECOND = "When,What,Howmuch\n2024-02-02,def,-7.00\n"
EXPORT = "Date,Payee,Narration,Amount,Currency,Category\n2026-08-02,Cafe,Coffee,-5.25,USD,Expenses:Food\n"
MAPPING = ("--csv", "date=When,narration=What,amount=Howmuch", "--account", "Assets:Bank")
NFC_NAME = "Café"


def _book(tmp_path: Path, directory: str) -> Path:
    books = tmp_path / directory
    books.mkdir()
    ledger = books / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "b.csv").write_text(FIRST)
    (tmp_path / "b2.csv").write_text(SECOND)
    (tmp_path / "bank.csv").write_text(EXPORT)
    return ledger


def _respelled(ledger: Path, directory: str) -> Path:
    """The same ledger through another spelling of its directory, where the volume has one."""
    other = ledger.parent.parent / directory
    if not (other.is_dir() and os.path.samefile(other, ledger.parent)):
        pytest.skip("this volume keeps the two spellings apart")
    return other / ledger.name


def _import(ledger: Path, source: str, *args: str) -> Result:
    return runner.invoke(
        app, ["--no-input", "--file", str(ledger), "import", str(ledger.parent.parent / source), *args]
    )


def _records(bea_config_dir: Path) -> list[Path]:
    return sorted((bea_config_dir / "importers").iterdir())


@pytest.mark.parametrize(
    ("stored", "typed"),
    [("Books", "books"), ("books", "BOOKS"), (unicodedata.normalize("NFD", NFC_NAME), NFC_NAME)],
    ids=["lower", "upper", "nfc"],
)
def test_a_csv_mapping_is_recalled_through_another_spelling(
    tmp_path: Path, bea_config_dir: Path, stored: str, typed: str
) -> None:
    ledger = _book(tmp_path, stored)
    other = _respelled(ledger, typed)
    applied = _import(ledger, "b.csv", *MAPPING, "--apply")
    assert applied.exit_code == 0, applied.output

    recalled = _import(other, "b2.csv")

    assert recalled.exit_code == 0, recalled.output
    assert "Using settings remembered from b.csv for b2.csv" in recalled.output
    assert '2024-02-02 ! "def"' in recalled.output
    control = _import(ledger, "b2.csv")
    assert control.exit_code == 0, control.output
    assert "Using settings remembered from b.csv for b2.csv" in control.output


def test_a_mapping_saved_through_another_spelling_shares_one_record(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = _book(tmp_path, "Books")
    other = _respelled(ledger, "books")

    applied = _import(other, "b.csv", *MAPPING, "--apply")

    assert applied.exit_code == 0, applied.output
    assert len(_records(bea_config_dir)) == 1
    recalled = _import(ledger, "b2.csv")
    assert recalled.exit_code == 0, recalled.output
    assert "Using settings remembered from b.csv for b2.csv" in recalled.output


def test_a_python_importer_is_recalled_through_another_spelling(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = _book(tmp_path, "Books")
    other = _respelled(ledger, "books")
    selected = _import(ledger, "bank.csv", "--config", str(CONFIG))
    assert selected.exit_code == 0, selected.output

    recalled = _import(other, "bank.csv")

    assert recalled.exit_code == 0, recalled.output
    assert "Coffee" in recalled.output
    assert "Choose a Python importer" not in recalled.output


def test_a_record_saved_under_the_typed_spelling_is_still_read(tmp_path: Path, bea_config_dir: Path) -> None:
    """Memory written before the fix keeps working for the spelling that wrote it."""
    ledger = _book(tmp_path, "Books")
    other = _respelled(ledger, "books")
    applied = _import(ledger, "b.csv", *MAPPING, "--apply")
    assert applied.exit_code == 0, applied.output
    (record,) = _records(bea_config_dir)
    legacy = record.with_name(f"csv-{hashlib.sha256(str(other.resolve()).encode()).hexdigest()}.json")
    assert legacy != record
    record.rename(legacy)

    recalled = _import(other, "b2.csv", "--apply")

    assert recalled.exit_code == 0, recalled.output
    assert "Using settings remembered from b.csv for b2.csv" in recalled.output


def test_another_ledger_recalls_nothing(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = _book(tmp_path, "Books")
    sibling = _book(tmp_path, "Other")
    applied = _import(ledger, "b.csv", *MAPPING, "--apply")
    assert applied.exit_code == 0, applied.output

    unrelated = _import(sibling, "b2.csv")

    assert unrelated.exit_code == 2, unrelated.output
    assert "Choose a Python importer" in unrelated.output


def test_a_name_no_directory_lists_keeps_its_typed_spelling(tmp_path: Path) -> None:
    from cli.commands.import_ import _stored_spelling

    ledger = _book(tmp_path, "Books")

    assert _stored_spelling(ledger) == ledger.resolve()
    assert _stored_spelling(tmp_path / "Books" / "Absent.bean") == (tmp_path / "Books").resolve() / "Absent.bean"
    assert _stored_spelling(tmp_path / "Missing" / "main.bean") == tmp_path.resolve() / "Missing" / "main.bean"
