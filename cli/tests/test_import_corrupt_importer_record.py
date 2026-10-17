"""A corrupt remembered-importer record never blocks a plain CSV import (w5/592).

Every read or parse failure of the ledger's record in `importers/` became one
pathless `Cannot read the saved importer path; select one with --config
FILE.`, exit 2. That stopped every flag-free CSV import, advising a Python
importer the CSV never needed. A corrupt record now selects nothing, as a
moved importer does (w5/141). One that cannot be read is still refused, but
it is named, with remedies that work.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from cli.main import app

runner = CliRunner()
LEDGER = (
    'option "operating_currency" "USD"\n2024-01-01 open Assets:Bank USD\n2024-01-01 open Expenses:Uncategorized USD\n'
)


@pytest.fixture
def ledger(tmp_path: Path, bea_config_dir: Path) -> Path:
    book = tmp_path / "main.bean"
    book.write_text(LEDGER)
    (tmp_path / "stmt.csv").write_text("Date,Amount,Description\n2024-02-01,-5.00,Coffee\n")
    return book


def _record(ledger: Path, bea_config_dir: Path, text: str) -> Path:
    directory = bea_config_dir / "importers"
    directory.mkdir(parents=True)
    record = directory / f"{hashlib.sha256(str(ledger.resolve()).encode()).hexdigest()}.json"
    record.write_text(text)
    return record


def _import(ledger: Path, *args: str) -> Result:
    return runner.invoke(app, ["--no-input", "--file", str(ledger), "import", str(ledger.parent / "stmt.csv"), *args])


@pytest.mark.parametrize(
    "text",
    ['{"config": "/x', "{}", "[]", '{"config": 5}', '{"config": null}', "[" * 5000 + "]" * 5000],
    ids=["truncated", "empty-object", "array", "number", "null", "deeply-nested"],
)
def test_a_corrupt_record_is_ignored_with_a_note_naming_it(ledger: Path, bea_config_dir: Path, text: str) -> None:
    record = _record(ledger, bea_config_dir, text)

    result = _import(ledger, "--account", "Assets:Bank")

    assert result.exit_code == 0, result.output
    message = " ".join(result.stderr.split())
    assert f"The remembered importer record {record} is not valid; ignoring it." in message
    assert "Read the column mapping from the header row" in message
    assert "csv → Assets:Bank: 1 ready" in result.stdout
    assert "Cannot read the saved importer path" not in message


def test_the_note_reaches_json(ledger: Path, bea_config_dir: Path) -> None:
    record = _record(ledger, bea_config_dir, "{}")

    result = runner.invoke(
        app,
        [
            "--json",
            "--no-input",
            "--file",
            str(ledger),
            "import",
            str(ledger.parent / "stmt.csv"),
            "--account",
            "Assets:Bank",
        ],
    )

    assert result.exit_code == 0, result.output
    notes = " ".join(json.loads(result.stdout)["data"]["notes"])
    assert f"The remembered importer record {record} is not valid" in notes


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="needs POSIX permissions that bind the user")
def test_an_unreadable_record_is_named_and_csv_auto_gets_past_it(ledger: Path, bea_config_dir: Path) -> None:
    record = _record(ledger, bea_config_dir, json.dumps({"config": str(ledger.parent / "importers.py")}))
    record.chmod(0)
    try:
        refused = _import(ledger, "--account", "Assets:Bank")
        auto = _import(ledger, "--account", "Assets:Bank", "--csv", "auto")
    finally:
        record.chmod(0o600)

    assert refused.exit_code == 2, refused.output
    message = " ".join(refused.stderr.split())
    assert f"Cannot read the remembered importer record {record} (Permission denied)" in message
    assert "--csv auto" in message and "--config FILE" in message
    assert auto.exit_code == 0, auto.output
    assert "csv → Assets:Bank: 1 ready" in auto.stdout
