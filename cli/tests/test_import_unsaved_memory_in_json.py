"""A `--json` import that could not save its settings says so in the envelope (w5/284).

With a config directory that cannot be written, text mode warned `Could not
remember the column mapping … Pass --csv on the next import.` on stderr, but
the JSON envelope of the same successful run said nothing, so an agent's next
flag-free import failed without having been told why.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner, Result

from cli.main import app

runner = CliRunner()

CONFIG = Path(__file__).resolve().parents[1] / "docs/examples/csv_importers.py"
MAPPING = "date=Date,amount=Amount,narration=Description"
CSV_NOTE = "Could not remember the column mapping: "
CSV_NEXT = "Pass --csv on the next import."
CONFIG_NOTE = "Could not remember the importer path: "
CONFIG_NEXT = "Pass --config on the next import."

posix_permissions = pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0, reason="needs POSIX permissions that bind the current user"
)


@pytest.fixture
def books(tmp_path: Path) -> Path:
    directory = tmp_path / "books"
    directory.mkdir()
    (directory / "main.bean").write_text(
        'option "operating_currency" "USD"\n'
        "2026-01-01 open Assets:Checking USD\n"
        "2026-01-01 open Expenses:Food\n"
        "2026-01-01 open Expenses:Uncategorized\n"
    )
    (directory / "apr.csv").write_text("Date,Description,Amount\n2026-04-02,Grocer,-20.00\n")
    (directory / "may.csv").write_text("Date,Description,Amount\n2026-05-02,Grocer,-4.50\n")
    (directory / "rules.toml").write_text('[[rule]]\nmatch = "grocer"\naccount = "Expenses:Food"\n')
    (directory / "bank.csv").write_text(
        "Date,Payee,Narration,Amount,Currency,Category\n2026-08-02,Cafe,Coffee,-5.25,USD,Expenses:Food\n"
    )
    shutil.copy(CONFIG, directory / "imp.py")
    return directory


@pytest.fixture
def read_only_config(bea_config_dir: Path) -> Iterator[Path]:
    """A config directory the import may read but not write, as in a sandbox."""
    bea_config_dir.mkdir(parents=True, exist_ok=True)
    bea_config_dir.chmod(0o555)
    try:
        yield bea_config_dir
    finally:
        bea_config_dir.chmod(0o700)


def _import(books: Path, source: str, *args: str, json_output: bool = True) -> Result:
    lead = ["--json"] if json_output else []
    ledger = books / "main.bean"
    return runner.invoke(app, [*lead, "--no-input", "--file", str(ledger), "import", str(books / source), *args])


def _first(books: Path, *args: str, json_output: bool = True) -> Result:
    explicit = ("--csv", MAPPING, "--account", "Assets:Checking", "--rules", str(books / "rules.toml"))
    return _import(books, "apr.csv", *explicit, *args, json_output=json_output)


def _data(result: Result) -> dict[str, Any]:
    assert result.exit_code == 0, result.output
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


@posix_permissions
@pytest.mark.parametrize("apply", [True, False], ids=["apply", "preview"])
def test_envelope_names_the_unsaved_column_mapping(books: Path, read_only_config: Path, apply: bool) -> None:
    result = _first(books, *(["--apply"] if apply else []))

    data = _data(result)
    assert data["written"] == (1 if apply else 0)
    unsaved = [note for note in data["notes"] if note.startswith(CSV_NOTE)]
    assert len(unsaved) == 1, data["notes"]
    assert str(read_only_config / "importers") in unsaved[0]
    assert unsaved[0].endswith(CSV_NEXT)
    # The run's own account of itself keeps its place ahead of the warning.
    assert data["notes"].index("Using column mapping (--csv).") < data["notes"].index(unsaved[0])
    assert result.stderr == ""
    assert not (read_only_config / "importers").exists()

    # Nothing was kept, which is what the note warned about.
    follow_up = _import(books, "may.csv", "--apply")
    assert follow_up.exit_code == 2, follow_up.output
    assert "not which account the export belongs to" in json.loads(follow_up.stderr)["error"]["message"]


@posix_permissions
def test_envelope_carries_the_statement_text_mode_makes(books: Path, read_only_config: Path) -> None:
    text = _first(books, json_output=False)
    assert text.exit_code == 0, text.output
    warnings = [line for line in text.stderr.splitlines() if line.startswith(CSV_NOTE)]
    assert len(warnings) == 1, text.stderr

    assert warnings[0] in _data(_first(books))["notes"]


@posix_permissions
def test_envelope_names_the_unsaved_importer_path(books: Path, read_only_config: Path) -> None:
    config = books / "imp.py"

    result = _import(books, "bank.csv", "--config", str(config))

    data = _data(result)
    assert data["ready"] == 1
    unsaved = [note for note in data["notes"] if note.startswith(CONFIG_NOTE)]
    assert len(unsaved) == 1, data["notes"]
    assert unsaved[0].endswith(CONFIG_NEXT)
    assert f"Using importers from {config} (--config)" in data["notes"]
    assert result.stderr == ""

    text = _import(books, "bank.csv", "--config", str(config), json_output=False)
    assert text.exit_code == 0, text.output
    assert unsaved[0] in text.stderr.splitlines()


def test_saved_memory_adds_no_note(books: Path, bea_config_dir: Path) -> None:
    first = _data(_first(books, "--apply"))
    assert first["written"] == 1
    assert first["notes"] == ["Using column mapping (--csv)."]

    second = _data(_import(books, "may.csv", "--apply"))
    assert second["written"] == 1
    assert second["config_source"] == "remembered --csv"
    assert not any(note.startswith("Could not remember") for note in second["notes"])

    with_importer = _data(_import(books, "bank.csv", "--config", str(books / "imp.py")))
    assert not any(note.startswith("Could not remember") for note in with_importer["notes"])
