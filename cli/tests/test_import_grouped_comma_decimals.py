"""A comma-decimal column with grouped thousands is inferred as comma decimals (w5/906).

The vote saw `1 234,567` while the parser read `1234,567`, so the column
fell back to point decimals and the amount was refused as invalid grouping.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea

LEDGER = 'option "operating_currency" "KWD"\n2024-01-01 open Assets:Cash KWD\n2024-01-01 open Expenses:Food KWD\n'
FILLERS = {
    "space": " ",
    "nbsp": " ",
    "narrow-nbsp": " ",
    "apostrophe": "'",
    "curly-apostrophe": "’",
}
IMPORT = ["import", "bank.csv", "--account", "Assets:Cash", "--default-account", "Expenses:Food", "--apply"]


def _books(tmp_path: Path, amount: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_text(f"Date;Description;Amount\n2024-02-01;Withdrawal;{amount}\n", encoding="utf-8")


def _cash(tmp_path: Path) -> Decimal:
    result = _bea(tmp_path, "query", "SELECT sum(number) WHERE account = 'Assets:Cash'")
    return Decimal(str(json.loads(result.stdout)["data"]["rows"][0][0]))


@pytest.mark.parametrize("filler", list(FILLERS.values()), ids=list(FILLERS))
def test_each_grouping_filler_imports_the_exact_amount(tmp_path: Path, filler: str) -> None:
    _books(tmp_path, f"-1{filler}234,567")

    applied = _bea(tmp_path, *IMPORT)

    assert applied.returncode == 0, applied.stderr
    assert _cash(tmp_path) == Decimal("-1234.567")
    assert _bea(tmp_path, "check").returncode == 0
    again = _bea(tmp_path, *IMPORT)
    assert json.loads(again.stdout)["data"]["written"] == 0


def test_an_explicit_mapping_infers_the_same(tmp_path: Path) -> None:
    _books(tmp_path, "-1 234,567")

    applied = _bea(tmp_path, *IMPORT, "--csv", "date=Date,amount=Amount,narration=Description")

    assert applied.returncode == 0, applied.stderr
    assert _cash(tmp_path) == Decimal("-1234.567")


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("-1 234,56", "-1234.56"), ("-1 234.567", "-1234.567"), ("-1234,567", "-1234.567")],
    ids=["two-decimals", "point-decimals", "ungrouped"],
)
def test_the_neighbouring_shapes_still_import(tmp_path: Path, amount: str, expected: str) -> None:
    _books(tmp_path, amount)

    applied = _bea(tmp_path, *IMPORT)

    assert applied.returncode == 0, applied.stderr
    assert _cash(tmp_path) == Decimal(expected)


def test_a_standalone_three_digit_group_stays_thousands(tmp_path: Path) -> None:
    _books(tmp_path, "-1,234")

    assert _bea(tmp_path, *IMPORT).returncode == 0
    assert _cash(tmp_path) == Decimal("-1234")


def test_mixed_conventions_are_still_refused(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_text("Date;Description;Amount\n2024-02-01;A;-1 234,567\n2024-02-02;B;-1,234.56\n")
    before = (tmp_path / "main.bean").read_bytes()

    refused = _bea(tmp_path, *IMPORT)

    assert refused.returncode == 2, refused.stdout
    assert (tmp_path / "main.bean").read_bytes() == before
