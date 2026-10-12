"""Standalone parse probes leave root names to the ledger's own options (w5/080).

A rendered directive parsed on its own runs under default options, so on a
ledger that renames its roots every account read as `Invalid account name`.
`add custom --value account:…` was always refused there, raw `ask` appends
were rejected, the bulk zero-net guard skipped itself, and an account-typed
`--meta` value degraded to a string.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"

RENAMED = """\
option "name_assets" "Aktiva"
option "name_expenses" "Aufwand"
option "name_equity" "Eigenkapital"
option "operating_currency" "EUR"
2026-01-01 open Aktiva:Bank EUR
2026-01-01 open Aufwand:Essen
2026-01-01 open Eigenkapital:OpeningBalances
"""
DEFAULT = """\
option "operating_currency" "EUR"
2026-01-01 open Assets:Bank EUR
2026-01-01 open Expenses:Food
2026-01-01 open Equity:OpeningBalances
"""
NAMES = {
    "renamed": (RENAMED, "Aktiva:Bank", "Aufwand:Essen"),
    "default": (DEFAULT, "Assets:Bank", "Expenses:Food"),
}


@pytest.fixture(params=["renamed", "default"])
def book(request: pytest.FixtureRequest, tmp_path: Path, bea_config_dir: Path) -> tuple[Path, str, str]:
    text, bank, food = NAMES[request.param]
    ledger = tmp_path / "main.bean"
    ledger.write_text(text)
    return ledger, bank, food


def _bea(ledger: Path, *args: str) -> Any:
    return runner.invoke(app, ["--file", str(ledger), *args])


def _engine(*args: str, stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bea_engine", *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )


def test_a_custom_directive_with_an_account_value_is_written_and_listed(book: tuple[Path, str, str]) -> None:
    ledger, _, food = book

    added = _bea(
        ledger, "add", "custom", "--date", "2026-01-02", "-t", "budget", "-v", f"account:{food}", "-v", "amount:400 EUR"
    )

    assert added.exit_code == 0, added.output
    assert f'2026-01-02 custom "budget" {food} 400 EUR' in ledger.read_text()
    assert _bea(ledger, "check").exit_code == 0
    listed = _bea(ledger, "list", "custom")
    assert f"account:{food} amount:400 EUR" in " ".join(listed.output.split())


def test_a_custom_account_value_under_an_unknown_root_is_still_refused(book: tuple[Path, str, str]) -> None:
    ledger, _, _ = book
    before = ledger.read_text()

    refused = _bea(ledger, "add", "custom", "--date", "2026-01-01", "-t", "budget", "-v", "account:Nowhere:Food")

    assert refused.exit_code != 0
    assert "Nowhere:Food" in refused.output
    assert ledger.read_text() == before


def test_a_raw_append_is_accepted(book: tuple[Path, str, str]) -> None:
    ledger, bank, food = book
    text = f'2026-02-01 * "Lunch"\n  {food}  5 EUR\n  {bank}\n'

    completed = _engine("append", "--file", str(ledger), "--text", "-", stdin=text)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["data"]["written"] == 1
    assert '2026-02-01 * "Lunch"' in ledger.read_text()


def test_a_bulk_row_whose_inferred_leg_is_zero_is_refused(book: tuple[Path, str, str]) -> None:
    ledger, bank, food = book
    before = ledger.read_text()
    rows = ledger.parent / "rows.json"
    rows.write_text(
        json.dumps(
            [
                {
                    "date": "2026-02-01",
                    "narration": "zero",
                    "postings": [
                        {"account": food, "amount": "5 EUR"},
                        {"account": food, "amount": "-5 EUR"},
                        {"account": bank},
                    ],
                }
            ]
        )
    )

    refused = _bea(ledger, "add", "transactions", "--from", str(rows))

    assert refused.exit_code == 1, refused.output
    assert "zero-net" in refused.output
    assert ledger.read_text() == before


def test_an_account_shaped_metadata_value_is_written_the_same_on_both_ledgers(book: tuple[Path, str, str]) -> None:
    ledger, bank, food = book

    added = _bea(
        ledger,
        "add",
        "transaction",
        "x",
        "--date",
        "2026-02-01",
        "-p",
        f"{food} 5 EUR",
        "-p",
        bank,
        "--meta",
        f"paid-from:{bank}",
    )

    assert added.exit_code == 0, added.output
    assert f'  paid-from: "{bank}"\n' in ledger.read_text()
    assert _bea(ledger, "check").exit_code == 0
