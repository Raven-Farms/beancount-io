"""A write into a file included through `..` names the user's file and honours `--allow-errors` (w5/096).

The snapshot kept `2026/../shared/tx.bean` as written while the loader
reported errors under the normalized name, so every lookup that maps a staged
copy back to its original missed: messages quoted a hidden `.bea-*.tmp` file,
and an error already in the destination read as newly introduced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

ROOT = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food
2026-01-01 open Expenses:Uncategorized
2026-01-01 open Equity:Opening
include "{include}"
"""
SHARED = """\
2026-01-02 * "Opening"
  Assets:Checking  1000.00 USD
  Equity:Opening
2026-01-10 balance Assets:Checking  5.00 USD
"""
LAYOUTS = {"dotdot": ("2026", "../shared/tx.bean"), "plain": (".", "shared/tx.bean")}


@pytest.fixture(params=sorted(LAYOUTS))
def books(request: pytest.FixtureRequest, tmp_path: Path, bea_config_dir: Path) -> tuple[Path, Path, str]:
    root_dir, include = LAYOUTS[request.param]
    (tmp_path / "shared").mkdir()
    (tmp_path / root_dir).mkdir(exist_ok=True)
    root = tmp_path / root_dir / "main.bean"
    root.write_text(ROOT.format(include=include))
    shared = tmp_path / "shared" / "tx.bean"
    shared.write_text(SHARED)
    return root, shared, include


def _bea(root: Path, *args: str) -> Any:
    return runner.invoke(app, ["--file", str(root), *args])


def _clean(result: Any, shared: Path) -> str:
    flat = " ".join(result.output.split())
    assert ".bea-" not in flat and "/../" not in flat, flat
    assert not list(shared.parent.glob(".bea-*"))
    return flat


def test_allow_errors_writes_over_an_error_already_in_the_destination(books: tuple[Path, Path, str]) -> None:
    root, shared, include = books

    result = _bea(
        root,
        "add",
        "transaction",
        "Lunch",
        "--date",
        "2026-02-01",
        "-p",
        "Expenses:Food 5 USD",
        "-p",
        "Assets:Checking",
        "--into",
        include,
        "--allow-errors",
    )

    assert result.exit_code == 0, result.output
    assert f"{shared}:4: Balance failed for 'Assets:Checking'" in _clean(result, shared)
    assert '2026-02-01 * "Lunch"' in shared.read_text()


@pytest.mark.parametrize("flags", [[], ["--allow-errors"]], ids=["plain", "allow-errors"])
def test_a_bad_write_is_refused_naming_the_real_file_and_the_append(
    books: tuple[Path, Path, str], flags: list[str]
) -> None:
    root, shared, include = books

    result = _bea(
        root,
        "add",
        "transaction",
        "Bad",
        "--date",
        "2026-02-01",
        "-p",
        "Expenses:Nope 5 USD",
        "-p",
        "Assets:Checking",
        "--into",
        include,
        *flags,
    )

    assert result.exit_code == 1, result.output
    flat = _clean(result, shared)
    assert "Proposed append (not written): Invalid reference to unknown account 'Expenses:Nope'" in flat
    if not flags:
        assert f"{shared}:4: Balance failed" in flat
    assert shared.read_text() == SHARED


def test_a_bulk_row_error_names_the_real_file(books: tuple[Path, Path, str]) -> None:
    root, shared, include = books
    rows = root.parent / "rows.json"
    rows.write_text(
        json.dumps(
            [
                {
                    "date": "2026-02-01",
                    "narration": "Bad",
                    "postings": [{"account": "Expenses:Nope", "amount": "5 USD"}, {"account": "Assets:Checking"}],
                }
            ]
        )
    )

    result = _bea(root, "add", "transactions", "--from", str(rows), "--into", include)

    assert result.exit_code == 1, result.output
    _clean(result, shared)
    assert shared.read_text() == SHARED


def test_an_import_into_the_destination_applies_over_the_existing_error(books: tuple[Path, Path, str]) -> None:
    root, shared, include = books
    source = root.parent / "bank.csv"
    source.write_text("Date,Description,Amount\n2026-02-03,Coffee,-4.50\n")

    result = _bea(
        root,
        "--no-input",
        "import",
        str(source),
        "--account",
        "Assets:Checking",
        "--into",
        include,
        "--apply",
        "--allow-errors",
    )

    assert result.exit_code == 0, result.output
    _clean(result, shared)
    assert '2026-02-03 ! "Coffee"' in shared.read_text()
