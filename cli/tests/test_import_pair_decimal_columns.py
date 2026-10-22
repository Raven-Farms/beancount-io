"""Debit and credit columns resolve their decimal convention independently (w5/895).

One vote across both columns read a lone grouped `1,234` in Debit as `1.234`
because Credit held a comma decimal `0,50`, writing the withdrawal 1000x small
with the counterposting to match, so the ledger stayed valid.
"""

from __future__ import annotations

import json
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea

LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
MAPPING = "date=Date,narration=Description,debit=Debit,credit=Credit"


def _run(tmp_path: Path, rows: str, mapping: str = MAPPING, *flags: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_text("Date,Description,Debit,Credit\n" + rows)
    return _bea(
        tmp_path, "import", "bank.csv", "--csv", mapping, "--account", "Assets:Cash",
        "--default-account", "Expenses:Food", *flags,
    )  # fmt: skip


def _cash(tmp_path: Path) -> dict[str, Decimal]:
    result = _bea(tmp_path, "query", "SELECT narration, number WHERE account = 'Assets:Cash' ORDER BY narration")
    return {name: Decimal(str(number)) for name, number in json.loads(result.stdout)["data"]["rows"]}


@pytest.mark.parametrize("mapping", [MAPPING, "auto"], ids=["explicit", "auto"])
def test_each_column_keeps_its_own_convention(tmp_path: Path, mapping: str) -> None:
    rows = '2024-02-01,Withdrawal,"1,234",\n2024-02-02,Refund,,"0,50"\n'

    applied = _run(tmp_path, rows, mapping, "--apply")

    assert applied.returncode == 0, applied.stderr
    assert _cash(tmp_path) == {"Refund": Decimal("0.50"), "Withdrawal": Decimal("-1234")}
    assert _bea(tmp_path, "check").returncode == 0


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ('2024-02-01,Withdrawal,"1,234",\n2024-02-02,Refund,,0.50\n', {"Refund": "0.50", "Withdrawal": "-1234"}),
        ('2024-02-01,Withdrawal,1234,\n2024-02-02,Refund,,"0,50"\n', {"Refund": "0.50", "Withdrawal": "-1234"}),
        (
            '2024-02-01,Withdrawal,"1,234.56",\n2024-02-02,Refund,,"0,50"\n',
            {"Refund": "0.50", "Withdrawal": "-1234.56"},
        ),
        (
            '2024-02-01,Withdrawal,"1.234,56",\n2024-02-02,Refund,,"0.50"\n',
            {"Refund": "0.50", "Withdrawal": "-1234.56"},
        ),
    ],
    ids=["point-credit", "plain-debit", "us-debit-eu-credit", "eu-debit-us-credit"],
)
def test_independent_valid_conventions_both_import(tmp_path: Path, rows: str, expected: dict[str, str]) -> None:
    applied = _run(tmp_path, rows, MAPPING, "--apply")

    assert applied.returncode == 0, applied.stderr
    assert _cash(tmp_path) == {name: Decimal(value) for name, value in expected.items()}


def test_a_column_that_mixes_conventions_is_still_refused(tmp_path: Path) -> None:
    before = LEDGER
    refused = _run(tmp_path, '2024-02-01,A,"1,000.00",\n2024-02-02,B,"1.000,00",\n', MAPPING, "--apply")

    assert refused.returncode == 2, refused.stdout
    assert "mix decimal conventions" in refused.stderr
    assert (tmp_path / "main.bean").read_text() == before


def test_an_explicit_override_still_governs_both_columns(tmp_path: Path) -> None:
    applied = _run(
        tmp_path, '2024-02-01,Withdrawal,"1,234",\n2024-02-02,Refund,,"0,50"\n', MAPPING + ",decimal=comma", "--apply"
    )

    assert applied.returncode == 0, applied.stderr
    assert _cash(tmp_path) == {"Refund": Decimal("0.50"), "Withdrawal": Decimal("-1.234")}
