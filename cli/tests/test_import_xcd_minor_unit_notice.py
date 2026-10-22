"""XCD has two minor-unit digits, so a three-decimal amount is not dot grouping (w5/907).

The no-minor-unit set listed XCD, so an ordinary `-650.000` was told its dots
likely group thousands; ISK, a genuine zero-decimal currency, keeps the notice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea

MAPPING = {
    "amount": "date=Date,narration=Description,amount=Amount",
    "debit-credit": "date=Date,narration=Description,debit=Debit,credit=Credit",
}
ROWS = {
    "amount": "Date;Description;Amount\n2024-02-01;Adjustment;-650.000\n",
    "debit-credit": "Date;Description;Debit;Credit\n2024-02-01;Adjustment;650.000;0\n",
}
NOTICE = "has no minor unit"


def _notes(tmp_path: Path, currency: str, layout: str, extra: str = "") -> list[str]:
    (tmp_path / "main.bean").write_text(
        f'option "operating_currency" "{currency}"\n2024-01-01 open Assets:Cash {currency}\n'
        f"2024-01-01 open Expenses:Food {currency}\n"
    )
    (tmp_path / "bank.csv").write_text(ROWS[layout])
    result = _bea(
        tmp_path, "import", "bank.csv", "--account", "Assets:Cash", "--default-account", "Expenses:Food",
        "--csv", MAPPING[layout] + extra,
    )  # fmt: skip
    assert result.returncode == 0, result.stderr
    return list(json.loads(result.stdout)["data"]["notes"])


@pytest.mark.parametrize("layout", list(MAPPING))
def test_xcd_gets_no_minor_unit_notice(tmp_path: Path, layout: str) -> None:
    assert not any(NOTICE in note for note in _notes(tmp_path, "XCD", layout))


@pytest.mark.parametrize("layout", list(MAPPING))
def test_a_genuine_zero_decimal_currency_keeps_the_notice(tmp_path: Path, layout: str) -> None:
    assert any(NOTICE in note and "ISK" in note for note in _notes(tmp_path, "ISK", layout))


def test_the_other_two_decimal_currencies_and_an_explicit_choice_stay_quiet(tmp_path: Path) -> None:
    assert not any(NOTICE in note for note in _notes(tmp_path, "USD", "amount"))
    assert not any(NOTICE in note for note in _notes(tmp_path, "ISK", "amount", ",decimal=point"))
