"""A currency symbol written before the negative marker still parses (w5/265).

`$-4.50` imported but `$-1,234.56` did not: the sign was split off only when
it came first, so with the symbol in front the grouping check saw `-1,234` and
refused a cell its own error listed as accepted. `€ -1.234,56` is the standard
Dutch currency format, and `$(1,234.56)` the same amount in parentheses.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bea_engine.csv_mapper import _parse_amount_cell, _resolve_decimal_comma
from bea_engine.protocol import UsageError
from cli.main import app

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Euro EUR
2026-01-01 open Expenses:Uncategorized
"""
WHERE = "Row 1 (line 2)"


def _preview(tmp_path: Path, text: str, mapping: str, account: str) -> list[dict[str, Any]]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    source = tmp_path / "bank.csv"
    source.write_text(text, encoding="utf-8")
    result = CliRunner().invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(source), "--csv", mapping, "--account", account],
    )
    assert result.exit_code == 0, result.output
    assert ledger.read_text() == LEDGER
    rows: list[dict[str, Any]] = json.loads(result.stdout)["data"]["rows"]
    return rows


@pytest.mark.parametrize("cell", ["$-1,234.56", "$ -1,234.56", "$(1,234.56)", "$ (1,234.56)", "(1,234.56) $"])
def test_a_point_column_reads_the_marker_after_the_symbol(cell: str) -> None:
    assert _parse_amount_cell(WHERE, "Amount", cell, decimal_comma=False) == Decimal("-1234.56")


@pytest.mark.parametrize("cell", ["€ -1.234,56", "€-1.234,56", "€ (1.234,56)"])
def test_a_comma_column_reads_the_marker_after_the_symbol(cell: str) -> None:
    assert _parse_amount_cell(WHERE, "Bedrag", cell, decimal_comma=True) == Decimal("-1234.56")


def test_a_plus_sign_after_the_symbol_parses() -> None:
    assert _parse_amount_cell(WHERE, "Amount", "$+1,234.56", decimal_comma=False) == Decimal("1234.56")


def test_a_signed_three_decimal_cell_still_proves_comma_decimals() -> None:
    assert _resolve_decimal_comma([(1, "€ -0,125")]) is True
    assert _resolve_decimal_comma([(1, "$-1,234")]) is False


@pytest.mark.parametrize("cell", ["-$(1,234.56)", "$(-1,234.56)", "($(1,234.56))", "$(1,234.56)-", "$-1,234.56-"])
def test_two_negative_markers_around_a_symbol_are_refused(cell: str) -> None:
    with pytest.raises(UsageError, match="marked negative twice"):
        _parse_amount_cell(WHERE, "Amount", cell, decimal_comma=False)


@pytest.mark.parametrize("cell", ["-$-1,234.56", "+$-1,234.56", "$--1,234.56", "$-1,23.56"])
def test_two_signs_or_bad_grouping_are_still_refused(cell: str) -> None:
    with pytest.raises(UsageError):
        _parse_amount_cell(WHERE, "Amount", cell, decimal_comma=False)


@pytest.mark.parametrize(
    ("cell", "decimal_comma", "expected"),
    [
        ("-$1,234.56", False, "-1234.56"),
        ("($1,234.56)", False, "-1234.56"),
        ("$-4.50", False, "-4.50"),
        ("$1,234.56", False, "1234.56"),
        ("-€ 1.234,56", True, "-1234.56"),
        ("€ 4,50-", True, "-4.50"),
    ],
)
def test_the_listed_controls_are_unchanged(cell: str, decimal_comma: bool, expected: str) -> None:
    assert _parse_amount_cell(WHERE, "Amount", cell, decimal_comma=decimal_comma) == Decimal(expected)


def test_import_previews_the_us_file(tmp_path: Path, bea_config_dir: Path) -> None:
    rows = _preview(
        tmp_path,
        'Date,Description,Amount\n2026-03-01,Rent,"$-1,234.56"\n2026-03-02,Fee,"$(2,000.00)"\n',
        "date=Date,amount=Amount,narration=Description",
        "Assets:Checking",
    )
    assert [(row["status"], row["amount"]) for row in rows] == [("new", "-1234.56 USD"), ("new", "-2000.00 USD")]


def test_import_previews_the_dutch_file(tmp_path: Path, bea_config_dir: Path) -> None:
    rows = _preview(
        tmp_path,
        "Datum;Omschrijving;Bedrag\n2026-03-01;Huur;€ -1.234,56\n2026-03-02;Koffie;€ -4,50\n",
        "date=Datum,amount=Bedrag,narration=Omschrijving",
        "Assets:Euro",
    )
    assert [(row["status"], row["amount"]) for row in rows] == [("new", "-1234.56 EUR"), ("new", "-4.50 EUR")]


def test_import_previews_the_leading_sign_control(tmp_path: Path, bea_config_dir: Path) -> None:
    rows = _preview(
        tmp_path,
        'Date,Description,Amount\n2026-03-01,Rent,"-$1,234.56"\n',
        "date=Date,amount=Amount,narration=Description",
        "Assets:Checking",
    )
    assert [(row["status"], row["amount"]) for row in rows] == [("new", "-1234.56 USD")]


def test_import_reads_a_credit_cell_with_the_symbol_first(tmp_path: Path, bea_config_dir: Path) -> None:
    rows = _preview(
        tmp_path,
        'Date,Description,Debit,Credit\n2026-03-01,Refund,,"$+1,234.56"\n',
        "date=Date,narration=Description,debit=Debit,credit=Credit",
        "Assets:Checking",
    )
    assert [(row["status"], row["amount"]) for row in rows] == [("new", "1234.56 USD")]
