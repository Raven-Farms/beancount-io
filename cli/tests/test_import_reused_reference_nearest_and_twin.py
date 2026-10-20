"""A reused bank reference is judged against the right entry (w5/822).

A row was judged against the latest entry under its native ID alone: January's
re-import was a conflict with February's different amount, which held back
every other row of the file. And an ID hit a month away hid the hand-entered
entry the row repeats on its own date, so the documented `--duplicates
include` booked that one twice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

HEAD = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Rent USD
2026-01-01 open Expenses:Uncategorized USD
"""
MAPPING = "date=Date,narration=Description,amount=Amount,id=Reference Number"


def _rent(date: str, month: str, amount: str, reference: bool = True) -> str:
    meta = '  import-id: "bank:RENT-AUTOPAY"\n' if reference else ""
    return f'{date} * "Rent {month}"\n{meta}  Assets:Checking  {amount} USD\n  Expenses:Rent\n'


@pytest.fixture
def books(tmp_path: Path, bea_config_dir: Path) -> Path:
    return tmp_path


def _import(books: Path, ledger_text: str, rows: str, *extra: str) -> tuple[int, dict[str, Any], Path]:
    ledger = books / "main.bean"
    ledger.write_text(HEAD + ledger_text)
    (books / "bank.csv").write_text("Date,Description,Amount,Reference Number\n" + rows)
    result = CliRunner().invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(books / "bank.csv")]
        + ["--csv", MAPPING, "--account", "Assets:Checking", *extra],
    )
    payload = json.loads(result.stdout if result.exit_code == 0 else result.stderr)
    data = payload["data"] if result.exit_code == 0 else payload["error"]["result"]
    return result.exit_code, data, ledger


def test_a_month_away_id_hit_names_the_same_day_twin(books: Path) -> None:
    ledger_text = _rent("2026-01-01", "January", "-1200.00") + _rent("2026-02-01", "February", "-1200.00", False)

    code, data, _ = _import(books, ledger_text, "2026-02-01,Rent February,-1200.00,RENT-AUTOPAY\n")

    assert code == 0, data
    (row,) = data["rows"]
    assert row["status"] == "possible_duplicate"
    assert row["reason"].startswith("Date, narration and source amount match; only one of them carries a bank ID.")
    assert "bank:RENT-AUTOPAY is already in the ledger on 2026-01-01, 31 days from this row" in row["reason"]
    assert row["match"]["entry"].startswith('2026-02-01 * "Rent February"')


def test_without_a_twin_the_month_away_id_hit_is_still_named(books: Path) -> None:
    code, data, _ = _import(
        books, _rent("2026-01-01", "January", "-1200.00"), "2026-02-01,Rent February,-1200.00,RENT-AUTOPAY\n"
    )

    assert code == 0, data
    (row,) = data["rows"]
    assert row["status"] == "possible_duplicate"
    assert row["reason"].startswith("Stable ID bank:RENT-AUTOPAY is already in the ledger on 2026-01-01")


def test_reimporting_a_month_matches_its_own_entry_under_a_reused_id(books: Path) -> None:
    ledger_text = _rent("2026-01-01", "January", "-1200.00") + _rent("2026-02-01", "February", "-1210.00")
    rows = "2026-01-01,Rent January,-1200.00,RENT-AUTOPAY\n2026-01-05,Coffee,-4.00,COFFEE-1\n"

    code, data, ledger = _import(books, ledger_text, rows, "--apply")

    assert code == 0, data
    assert [(row["narration"], row["status"]) for row in data["rows"]] == [
        ("Rent January", "duplicate"),
        ("Coffee", "new"),
    ]
    assert data["written"] == 1
    assert '"Coffee"' in ledger.read_text()


def test_different_amounts_under_every_entry_are_still_a_conflict(books: Path) -> None:
    ledger_text = _rent("2026-01-01", "January", "-1200.00") + _rent("2026-02-01", "February", "-1210.00")

    code, data, _ = _import(books, ledger_text, "2026-01-01,Rent January,-1250.00,RENT-AUTOPAY\n")

    assert code == 0, data
    (row,) = data["rows"]
    assert row["status"] == "conflict"
