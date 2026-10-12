"""`--allow-errors` never lets a write leave a pad unused, except the pad `add pad` stages (w5/081).

The staged-pad carve-out exempted every `Unused Pad` error from any command,
so a clean ledger could be left failing `bea check` by a write that exited 0.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Cash
2026-01-01 open Expenses:Food
2026-01-01 open Expenses:Uncategorized
2026-01-01 open Equity:Opening

2026-01-02 * "Open"
  Assets:Checking  5000.00 USD
  Equity:Opening
"""
PADDED = LEDGER + "2026-01-09 pad Assets:Cash Equity:Opening\n2026-01-10 balance Assets:Cash  50.00 USD\n"


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _bea(book: Path, *args: str) -> Any:
    return runner.invoke(app, ["--file", str(book), *args])


def _check(book: Path) -> int:
    return int(_bea(book, "check").exit_code)


@pytest.mark.parametrize("flags", [[], ["--allow-errors"]], ids=["plain", "allow-errors"])
def test_pad_from_writes_the_assertion_alone_when_the_book_already_matches(book: Path, flags: list[str]) -> None:
    result = _bea(
        book,
        "--json",
        "add",
        "balance",
        "--date",
        "2026-02-01",
        "-a",
        "Assets:Checking",
        "--amount",
        "5000.00 USD",
        "--pad-from",
        "Equity:Opening",
        *flags,
    )

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    assert data["written"] == 1
    assert any("omitted the pad" in warning for warning in data["warnings"])
    assert " pad " not in book.read_text()
    assert _check(book) == 0


@pytest.mark.parametrize("flags", [[], ["--allow-errors"]], ids=["plain", "allow-errors"])
def test_a_write_that_orphans_an_existing_pad_is_refused(book: Path, flags: list[str]) -> None:
    book.write_text(PADDED)
    assert _check(book) == 0

    result = _bea(
        book,
        "add",
        "transaction",
        "found it",
        "--date",
        "2026-01-05",
        "-p",
        "Assets:Cash 50.00 USD",
        "-p",
        "Equity:Opening",
        *flags,
    )

    assert result.exit_code == 1, result.output
    flat = " ".join(result.output.split())
    assert f"{book}:11: Unused Pad entry" in flat
    assert "--pad-from" not in flat
    assert book.read_text() == PADDED
    assert _check(book) == 0


def test_an_import_that_orphans_an_existing_pad_is_refused(book: Path) -> None:
    book.write_text(PADDED)
    source = book.parent / "cash.csv"
    source.write_text("Date,Description,Amount\n2026-01-05,Found it,50.00\n")

    result = _bea(book, "--no-input", "import", str(source), "--account", "Assets:Cash", "--apply", "--allow-errors")

    assert result.exit_code == 1, result.output
    assert "Unused Pad" in result.output
    assert book.read_text() == PADDED
    assert _check(book) == 0


def test_add_pad_still_stages_its_own_pad_for_the_two_step_flow(book: Path) -> None:
    refused = _bea(book, "add", "pad", "--date", "2026-01-09", "-a", "Assets:Cash", "-s", "Equity:Opening")
    assert refused.exit_code == 1, refused.output

    staged = _bea(
        book, "add", "pad", "--date", "2026-01-09", "-a", "Assets:Cash", "-s", "Equity:Opening", "--allow-errors"
    )
    assert staged.exit_code == 0, staged.output
    assert _check(book) == 1
    balance = _bea(book, "add", "balance", "--date", "2026-01-10", "-a", "Assets:Cash", "--amount", "50.00 USD")

    assert balance.exit_code == 0, balance.output
    assert _check(book) == 0


def test_add_pad_may_not_orphan_a_pad_that_was_valid_before(book: Path) -> None:
    book.write_text(PADDED)

    result = _bea(
        book, "add", "pad", "--date", "2026-01-09", "-a", "Assets:Cash", "-s", "Expenses:Food", "--allow-errors"
    )

    assert result.exit_code == 1, result.output
    assert book.read_text() == PADDED
