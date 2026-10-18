"""A row and an entry, one with a payee and one without, meet on their narration (w5/602).

The existing entry was keyed by its payee when it had one, and a
one-description row by its narration, so the two never met. A bank export of
rows beancount-migrate had written as payee + statement text (Monarch's
shape) was booked again, exit 0. Two named payees still never meet on a
shared narration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
HEADER = """option "operating_currency" "USD"

2026-09-01 open Assets:Checking USD
2026-09-01 open Expenses:Dining USD
2026-09-01 open Expenses:Uncategorized USD

"""
ENTRY = "2026-09-28 * {title}\n  Assets:Checking  -4.50 USD\n  Expenses:Dining   4.50 USD\n"


def _import(tmp_path: Path, title: str, csv: str, mapping: str) -> tuple[Path, bytes, dict[str, Any]]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(HEADER + ENTRY.format(title=title))
    before = ledger.read_bytes()
    (tmp_path / "bank.csv").write_text(csv)
    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(tmp_path / "bank.csv"), "--csv", mapping]
        + ["--account", "Assets:Checking", "--duplicates", "skip", "--apply"],
    )
    assert result.exit_code == 0, result.output
    return ledger, before, json.loads(result.stdout)["data"]


@pytest.mark.parametrize(
    ("title", "csv", "mapping"),
    [
        (
            '"Starbucks" "CARD PURCHASE 1234"',
            "Date,Description,Amount\n2026-09-28,CARD PURCHASE 1234,-4.50\n",
            "date=Date,narration=Description,amount=Amount",
        ),
        (
            '"CARD PURCHASE 1234"',
            "Date,Payee,Description,Amount\n2026-09-28,Starbucks,CARD PURCHASE 1234,-4.50\n",
            "date=Date,payee=Payee,narration=Description,amount=Amount",
        ),
    ],
    ids=["entry-has-the-payee", "row-has-the-payee"],
)
def test_one_side_without_a_payee_is_a_possible_duplicate(tmp_path: Path, title: str, csv: str, mapping: str) -> None:
    ledger, before, data = _import(tmp_path, title, csv, mapping)

    (row,) = data["rows"]
    assert row["status"] == "possible_duplicate"
    assert data["written"] == 0
    assert ledger.read_bytes() == before


def test_two_named_payees_never_meet_on_a_shared_narration(tmp_path: Path) -> None:
    ledger, before, data = _import(
        tmp_path,
        '"Starbucks" "POS PURCHASE"',
        "Date,Payee,Description,Amount\n2026-09-28,Peets,POS PURCHASE,-4.50\n",
        "date=Date,payee=Payee,narration=Description,amount=Amount",
    )

    (row,) = data["rows"]
    assert row["status"] == "new"
    assert data["written"] == 1
