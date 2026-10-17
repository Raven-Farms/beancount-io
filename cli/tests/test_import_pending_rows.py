"""A card export's pending rows can be left out until they post (w5/614).

Every row was imported, the mapping had no status field, and nothing said
what to do: a pending charge that posted days later at another amount (a
tip, a hold) was booked twice. `status=COLUMN` now leaves pending rows out
and names them; an unmapped column that marks rows pending gets a note; a
`Status` header is mapped by inference.
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
    "2026-01-01 open Liabilities:CreditCard USD\n"
    "2026-01-01 open Expenses:Dining\n"
    "2026-01-01 open Expenses:Uncategorized\n"
)
HEADER = "Transaction Date,Description,Amount,Status\n"
MAPPING = "date=Transaction Date,narration=Description,amount=Amount"


@pytest.fixture
def books(tmp_path: Path, bea_config_dir: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "sep.csv").write_text(
        HEADER + "09/27/2026,BISTRO 9,-50.00,Pending\n09/28/2026,BLUE BOTTLE,-4.50,Posted\n"
    )
    (tmp_path / "oct.csv").write_text(HEADER + "09/27/2026,BISTRO 9,-58.00,Posted\n10/02/2026,CAFE,-5.00,Posted\n")
    return tmp_path


def _import(books: Path, name: str, *args: str) -> dict[str, Any]:
    result = runner.invoke(
        app, ["--json", "--no-input", "--file", str(books / "main.bean"), "import", str(books / name), *args]
    )
    assert result.exit_code == 0, result.output
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def _card(books: Path) -> str:
    result = runner.invoke(
        app, ["--json", "--file", str(books / "main.bean"), "query", "SELECT sum(number) WHERE account ~ 'CreditCard'"]
    )
    return str(json.loads(result.stdout)["data"]["rows"][0][0])


def test_two_months_end_at_the_posted_balance(books: Path) -> None:
    sep = _import(
        books, "sep.csv", "--csv", f"{MAPPING},status=Status", "--account", "Liabilities:CreditCard", "--apply"
    )

    assert sep["skipped_pending"] == 1
    assert any("Left out 1 pending row(s) (09/27/2026 BISTRO 9 -50.00)" in note for note in sep["notes"])
    oct_ = _import(books, "oct.csv", "--apply")
    assert oct_["written"] == 2
    assert _card(books) == "-67.50"


def test_an_unmapped_status_column_is_named(books: Path) -> None:
    data = _import(books, "sep.csv", "--csv", MAPPING, "--account", "Liabilities:CreditCard")

    assert data["skipped_pending"] == 0
    assert data["ready"] == 2
    assert any("Column 'Status' marks 1 row(s) pending" in note and "status=Status" in note for note in data["notes"])


def test_a_status_header_is_mapped_by_inference(books: Path) -> None:
    data = _import(books, "sep.csv", "--account", "Liabilities:CreditCard")

    assert data["ready"] == 1
    assert data["skipped_pending"] == 1
