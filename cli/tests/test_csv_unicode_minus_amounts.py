"""A typographic minus in a CSV amount is the minus sign it looks like (w5/255).

Some bank and spreadsheet exports write negatives with `−` (U+2212), which no
viewer distinguishes from `-`. The cell was refused as unparseable, with an
error that showed a perfectly ordinary-looking `−4.50`; a zero-width space
beside the number was refused the same way.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bea_engine.csv_mapper import _parse_amount_cell
from bea_engine.protocol import UsageError
from cli.main import app

LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Bank:Checking USD
2024-01-01 open Expenses:Uncategorized
"""
MINUS = "−"
ZWSP = "​"


def _preview(tmp_path: Path, header: str, row: str, mapping: str) -> list[dict[str, Any]]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    source = tmp_path / "bank.csv"
    source.write_text(f"{header}\n{row}\n", encoding="utf-8")
    result = CliRunner().invoke(
        app,
        [
            "--json",
            "--no-input",
            "--file",
            str(ledger),
            "import",
            str(source),
            "--csv",
            mapping,
            "--account",
            "Assets:Bank:Checking",
        ],
    )
    assert result.exit_code == 0, result.output
    assert ledger.read_text() == LEDGER
    rows: list[dict[str, Any]] = json.loads(result.stdout)["data"]["rows"]
    return rows


@pytest.mark.parametrize(
    "cell",
    [
        f"{MINUS}4.50",
        f"4.50{MINUS}",
        f"{MINUS}$4.50",
        f"${MINUS}4.50",
        f"-4.50{ZWSP}",
        f"{ZWSP}-4.50",
        f"{MINUS}{ZWSP}4.50",
        "﻿-4.50",
    ],
)
def test_a_typographic_minus_or_zero_width_space_parses(cell: str) -> None:
    assert _parse_amount_cell("Row 1 (line 2)", "Amount", cell, decimal_comma=False) == Decimal("-4.50")


def test_a_comma_decimal_column_reads_the_typographic_minus() -> None:
    parsed = _parse_amount_cell("Row 1 (line 2)", "Amount", f"{MINUS}1.234,50 €", decimal_comma=True)
    assert parsed == Decimal("-1234.50")


@pytest.mark.parametrize("cell", [f"({MINUS}4.50)", f"{MINUS}4.50{MINUS}", f"-4.50{MINUS}", f"{MINUS}4.50-"])
def test_a_typographic_minus_still_counts_as_a_negative_marker(cell: str) -> None:
    with pytest.raises(UsageError, match="marked negative twice"):
        _parse_amount_cell("Row 1 (line 2)", "Amount", cell, decimal_comma=False)


@pytest.mark.parametrize("cell", ["-4.50", "4.50-", "(4.50)"])
def test_the_ascii_spellings_are_unchanged(cell: str) -> None:
    assert _parse_amount_cell("Row 1 (line 2)", "Amount", cell, decimal_comma=False) == Decimal("-4.50")


@pytest.mark.parametrize("cell", [f"{MINUS}4.50", f"-4.50{ZWSP}", "-4.50"])
def test_import_previews_the_amount_column(tmp_path: Path, bea_config_dir: Path, cell: str) -> None:
    rows = _preview(
        tmp_path, "Date,Description,Amount", f"2024-03-01,Coffee,{cell}", "date=Date,payee=Description,amount=Amount"
    )
    assert [(row["status"], row["amount"]) for row in rows] == [("new", "-4.50 USD")]
    assert "Assets:Bank:Checking    -4.50 USD" in rows[0]["entry"]


def test_import_previews_debit_and_credit_columns(tmp_path: Path, bea_config_dir: Path) -> None:
    rows = _preview(
        tmp_path,
        "Date,Description,Debit,Credit",
        f"2024-03-01,Coffee,4.50{ZWSP},{MINUS}0.00",
        "date=Date,payee=Description,debit=Debit,credit=Credit",
    )
    assert [(row["status"], row["amount"]) for row in rows] == [("new", "-4.50 USD")]
