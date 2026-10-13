"""An import-memory directory that cannot be read never blocks `bea import` (w5/215)."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

MAPPING = "date=Date,amount=Amount,narration=Description"

pytestmark = pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0, reason="needs POSIX permissions that bind the current user"
)


@pytest.fixture
def books(tmp_path: Path) -> tuple[Path, Path]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        'option "operating_currency" "USD"\n'
        "2026-01-01 open Assets:Checking USD\n"
        "2026-01-01 open Expenses:Uncategorized USD\n"
    )
    source = tmp_path / "checking.csv"
    source.write_text("Date,Description,Amount\n2026-02-02,Grocer,-20.00\n2026-02-03,Cafe,-4.50\n")
    return ledger, source


@pytest.fixture
def memory(books: tuple[Path, Path], bea_config_dir: Path) -> Iterator[Path]:
    """The memory directory, seeded by one preview, restored to a removable mode afterwards."""
    ledger, source = books
    seeded = CliRunner().invoke(app, ["--file", str(ledger), "import", str(source), "--account", "Assets:Checking"])
    assert seeded.exit_code == 0, seeded.output
    directory = bea_config_dir / "importers"
    assert [record.name for record in directory.iterdir()]
    try:
        yield directory
    finally:
        bea_config_dir.chmod(0o700)
        directory.chmod(0o700)


def _unreadable(memory: Path, target: str) -> None:
    (memory if target == "importers" else memory.parent).chmod(0)


@pytest.mark.parametrize("target", ["importers", "config"])
def test_fully_specified_apply_writes_and_names_the_unreadable_directory(
    books: tuple[Path, Path], memory: Path, target: str
) -> None:
    ledger, source = books
    _unreadable(memory, target)

    result = CliRunner().invoke(
        app,
        ["--file", str(ledger), "import", str(source), "--csv", MAPPING, "--account", "Assets:Checking", "--apply"],
    )

    assert result.exit_code == 0, result.output
    assert "[Errno" not in result.output
    assert "Could not remember" not in result.stderr
    assert result.stderr.count(f"Cannot read remembered import settings in {memory} (Permission denied)") == 1
    assert "this run is not remembered" in result.stderr
    written = ledger.read_text()
    assert written.count('"Grocer"') == 1 and written.count('"Cafe"') == 1


def test_flag_light_preview_proceeds_from_the_header_row(books: tuple[Path, Path], memory: Path) -> None:
    ledger, source = books
    before = ledger.read_bytes()
    memory.chmod(0)
    args = ["--file", str(ledger), "import", str(source), "--account", "Assets:Checking"]

    shown = CliRunner().invoke(app, args)
    structured = CliRunner().invoke(app, ["--json", *args])

    assert shown.exit_code == 0, shown.output
    assert "[Errno" not in shown.output
    assert f"Cannot read remembered import settings in {memory}" in shown.stderr
    assert "Read the column mapping from the header row" in shown.stderr
    assert structured.exit_code == 0, structured.output
    assert "[Errno" not in structured.output
    data = json.loads(structured.stdout)["data"]
    assert data["ready"] == 2
    assert data["config_source"] == "inferred --csv"
    assert data["remembered"] is None
    assert sum(f"Cannot read remembered import settings in {memory}" in note for note in data["notes"]) == 1
    assert ledger.read_bytes() == before


def test_python_importer_run_without_memory_names_the_directory_in_its_refusal(
    books: tuple[Path, Path], memory: Path
) -> None:
    """With nothing to fall back on, the refusal is the documented usage error, not the raw OS one."""
    ledger, source = books
    source.write_text("no recognizable header\n1,2\n")
    memory.chmod(0)

    result = CliRunner().invoke(app, ["--json", "--file", str(ledger), "import", str(source)])

    assert result.exit_code == 2, result.output
    assert "[Errno" not in result.output
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert "Choose a Python importer with --config FILE" in error["message"]
    assert f"Cannot read remembered import settings in {memory}" in json.dumps(error)


def test_read_only_directory_still_recalls_and_notes_the_failed_save(books: tuple[Path, Path], memory: Path) -> None:
    """Control: memory that can be read is used; only saving degrades, as before."""
    ledger, source = books
    memory.chmod(0o555)
    base = ["--file", str(ledger), "import", str(source)]

    recalled = CliRunner().invoke(app, base)
    typed = CliRunner().invoke(app, [*base, "--csv", MAPPING, "--account", "Assets:Checking", "--apply"])

    assert recalled.exit_code == 0, recalled.output
    assert "Using remembered settings for checking.csv" in recalled.stderr
    assert "Cannot read remembered import settings" not in recalled.stderr
    assert typed.exit_code == 0, typed.output
    assert "Could not remember the column mapping" in typed.stderr
    assert "Cannot read remembered import settings" not in typed.stderr
    assert ledger.read_text().count('"Grocer"') == 1


def test_unreadable_saved_importer_record_is_a_usage_error(books: tuple[Path, Path], memory: Path) -> None:
    ledger, source = books
    source.write_text("no recognizable header\n1,2\n")
    record = memory / f"{hashlib.sha256(str(ledger.resolve()).encode()).hexdigest()}.json"
    record.write_text(json.dumps({"config": str(ledger.parent / "importers.py")}))
    record.chmod(0)

    result = CliRunner().invoke(app, ["--json", "--file", str(ledger), "import", str(source)])

    assert result.exit_code == 2, result.output
    assert "[Errno" not in result.output
    assert "Cannot read the saved importer path" in json.loads(result.stderr)["error"]["message"]
