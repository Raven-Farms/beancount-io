"""Unsigned magnitudes with a direction column import signed (w5/755).

`Type` holding DEBIT/CREDIT (D/C, Dr/Cr, Af/Bij) maps with `direction=Column`:
the column decides each row's sign and the cell supplies only the magnitude,
as with the debit/credit pair. An unmapped direction-shaped column beside
unsigned amounts is refused naming the column — otherwise every debit books
as money in, exit 0. Signed amounts carry their own direction, so the column
stays redundant and silent there.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bea_engine.csv_mapper import _directed_number
from bea_engine.csv_mapper import parse_mapping as engine_parse_mapping
from bea_engine.protocol import UsageError
from cli.csv_mapper import parse_mapping as frontend_parse_mapping
from cli.errors import UsageError as FrontendUsageError
from cli.main import app

runner = CliRunner()
MAPPING = "date=Date,amount=Amount,narration=Description"
LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Expenses:Uncategorized USD\n"
)
TYPE_CSV = (
    "Date,Description,Amount,Type,Balance\n"
    "2026-01-02,Coffee shop,4.50,DEBIT,995.50\n"
    "2026-01-03,Payroll,2000.00,CREDIT,2995.50\n"
    "2026-01-04,Rent,1200.00,DEBIT,1795.50\n"
)


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "type.csv").write_text(TYPE_CSV)
    return ledger


def _import(book: Path, name: str, *args: str) -> dict[str, Any]:
    result = runner.invoke(app, ["--json", "--file", str(book), "import", str(book.parent / name), *args])
    assert result.exit_code == 0, result.output
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def _refuse(book: Path, name: str, *args: str) -> str:
    result = runner.invoke(app, ["--json", "--file", str(book), "import", str(book.parent / name), *args])
    assert result.exit_code == 2, result.output
    return result.output


def _checking_line(book: Path, amount: str) -> bool:
    return re.search(rf"^\s+Assets:Checking\s+{re.escape(amount)} USD$", book.read_text(), re.MULTILINE) is not None


def test_direction_column_imports_signed_amounts(book: Path) -> None:
    preview = _import(book, "type.csv", "--account", "Assets:Checking", "--csv", f"{MAPPING},direction=Type")
    assert [row["amount"] for row in preview["rows"]] == ["-4.50 USD", "2000.00 USD", "-1200.00 USD"]

    applied = _import(book, "type.csv", "--account", "Assets:Checking", "--csv", f"{MAPPING},direction=Type", "--apply")
    assert applied["written"] == 3
    assert _checking_line(book, "-4.50") and _checking_line(book, "2000.00") and _checking_line(book, "-1200.00")

    check = runner.invoke(app, ["--file", str(book), "check"])
    assert check.exit_code == 0, check.output


@pytest.mark.parametrize(
    ("debit", "credit"),
    [("D", "C"), ("Dr", "Cr"), ("Af", "Bij"), ("debit", "credit"), ("  Dr  ", "  Cr  ")],
)
def test_direction_word_variants(book: Path, debit: str, credit: str) -> None:
    (book.parent / "words.csv").write_text(
        f"Date,Description,Amount,Type\n2026-01-02,Out,4.50,{debit}\n2026-01-03,In,9.00,{credit}\n"
    )
    preview = _import(book, "words.csv", "--account", "Assets:Checking", "--csv", f"{MAPPING},direction=Type")
    assert [row["amount"] for row in preview["rows"]] == ["-4.50 USD", "9.00 USD"]


def test_direction_column_wins_over_cell_signs(book: Path) -> None:
    (book.parent / "signed.csv").write_text(
        "Date,Description,Amount,Type\n"
        "2026-01-02,Out,-4.50,DEBIT\n"
        "2026-01-03,Out,7.00,DEBIT\n"
        "2026-01-04,In,-2000.00,CREDIT\n"
    )
    preview = _import(book, "signed.csv", "--account", "Assets:Checking", "--csv", f"{MAPPING},direction=Type")
    assert [row["amount"] for row in preview["rows"]] == ["-4.50 USD", "-7.00 USD", "2000.00 USD"]


def test_unknown_direction_word_is_refused(book: Path) -> None:
    (book.parent / "bad.csv").write_text(
        "Date,Description,Amount,Type\n2026-01-02,X,4.50,DEBIT\n2026-01-03,Y,5.50,MAYBE\n"
    )
    before = book.read_bytes()
    output = _refuse(book, "bad.csv", "--account", "Assets:Checking", "--csv", f"{MAPPING},direction=Type")
    assert "Row 2 (line 3): unknown direction 'MAYBE' in column 'Type'" in output
    assert book.read_bytes() == before


def test_blank_direction_is_refused(book: Path) -> None:
    (book.parent / "blank.csv").write_text(
        "Date,Description,Amount,Type\n2026-01-02,X,4.50,DEBIT\n2026-01-03,Y,5.50,\n"
    )
    before = book.read_bytes()
    output = _refuse(book, "blank.csv", "--account", "Assets:Checking", "--csv", f"{MAPPING},direction=Type")
    assert "Row 2 (line 3): empty direction in column 'Type'" in output
    assert book.read_bytes() == before


def test_unmapped_direction_column_is_refused_naming_it(book: Path) -> None:
    before = book.read_bytes()
    output = _refuse(book, "type.csv", "--account", "Assets:Checking")
    assert "Column 'Type' looks like a direction column ('DEBIT', ...)" in output
    assert "Add direction=Type to the --csv mapping" in output
    assert book.read_bytes() == before


def test_unmapped_abbreviations_need_a_direction_name(book: Path) -> None:
    (book.parent / "abbr.csv").write_text("Date,Description,Amount,Type\n2026-01-02,X,4.50,D\n2026-01-03,Y,5.50,C\n")
    output = _refuse(book, "abbr.csv", "--account", "Assets:Checking")
    assert "Column 'Type' looks like a direction column" in output

    (book.parent / "grade.csv").write_text("Date,Description,Amount,Grade\n2026-01-02,X,4.50,C\n2026-01-03,Y,5.50,D\n")
    preview = _import(book, "grade.csv", "--account", "Assets:Checking")
    assert [row["amount"] for row in preview["rows"]] == ["4.50 USD", "5.50 USD"]


def test_full_direction_words_refuse_under_any_header(book: Path) -> None:
    (book.parent / "weird.csv").write_text(
        "Date,Description,Amount,Weird\n2026-01-02,X,4.50,DEBIT\n2026-01-03,Y,5.50,CREDIT\n"
    )
    output = _refuse(book, "weird.csv", "--account", "Assets:Checking")
    assert "Column 'Weird' looks like a direction column" in output


def test_signed_amounts_make_the_column_redundant(book: Path) -> None:
    (book.parent / "signed-no-map.csv").write_text(
        "Date,Description,Amount,Type\n2026-01-02,X,-4.50,DEBIT\n2026-01-03,Y,2000.00,CREDIT\n"
    )
    preview = _import(book, "signed-no-map.csv", "--account", "Assets:Checking")
    assert [row["amount"] for row in preview["rows"]] == ["-4.50 USD", "2000.00 USD"]
    assert not any("direction column" in note for note in preview["notes"])


def test_pair_mode_ignores_a_type_column(book: Path) -> None:
    (book.parent / "pair.csv").write_text(
        "Date,Description,Out,In,Type\n2026-01-02,X,4.50,,DEBIT\n2026-01-03,Y,,2000.00,CREDIT\n"
    )
    preview = _import(
        book, "pair.csv", "--account", "Assets:Checking", "--csv", "date=Date,narration=Description,debit=Out,credit=In"
    )
    assert [row["amount"] for row in preview["rows"]] == ["-4.50 USD", "2000.00 USD"]


def test_direction_with_pair_is_refused(book: Path) -> None:
    output = _refuse(
        book,
        "type.csv",
        "--account",
        "Assets:Checking",
        "--csv",
        "date=Date,narration=Description,debit=Amount,credit=Balance,direction=Type",
    )
    assert "combines with amount=Column, not with debit=A,credit=B" in output
    with pytest.raises(UsageError, match="combines with amount=Column"):
        engine_parse_mapping("date=D,narration=N,debit=A,credit=B,direction=T")


def test_direction_with_sign_ledger_is_refused(book: Path) -> None:
    output = _refuse(book, "type.csv", "--account", "Assets:Checking", "--csv", f"{MAPPING},direction=Type,sign=ledger")
    assert "already decides each row's direction; drop sign=ledger" in output
    with pytest.raises(UsageError, match="drop sign=ledger"):
        engine_parse_mapping("date=D,amount=A,narration=N,direction=T,sign=ledger")
    with pytest.raises(FrontendUsageError, match="drop sign=ledger"):
        frontend_parse_mapping("date=D,amount=A,narration=N,direction=T,sign=ledger")


class TestDirectedNumber:
    @pytest.mark.parametrize(
        ("number", "cell", "expected"),
        [
            ("4.50", "DEBIT", "-4.50"),
            ("4.50", "d", "-4.50"),
            ("-4.50", "DEBIT", "-4.50"),
            ("4.50", "CREDIT", "4.50"),
            ("-2000.00", "Cr", "2000.00"),
            ("4.50", "Af", "-4.50"),
            ("4.50", "Bij", "4.50"),
        ],
    )
    def test_column_decides_sign_magnitude_survives(self, number: str, cell: str, expected: str) -> None:
        assert _directed_number(Decimal(number), cell, "Row 1 (line 2)", "Type") == Decimal(expected)

    def test_unknown_word_names_row_column_and_words(self) -> None:
        with pytest.raises(UsageError, match=r"Row 2 \(line 3\): unknown direction 'MAYBE' in column 'Type'"):
            _directed_number(Decimal("5.50"), "MAYBE", "Row 2 (line 3)", "Type")

    def test_blank_direction_names_row_and_column(self) -> None:
        with pytest.raises(UsageError, match=r"Row 2 \(line 3\): empty direction in column 'Type'"):
            _directed_number(Decimal("5.50"), "   ", "Row 2 (line 3)", "Type")
