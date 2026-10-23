"""Each transfer pairs with one row of the other bank's export, and each row with one transfer (w5/882).

Every transfer chose the row nearest it on its own, so two transfers could
claim one row and leave the other row booked as a third transfer; and a
same-day deposit could take the transfer a shared bank reference already
named, so `--duplicates skip` dropped a real deposit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

OPENS = (
    "2024-01-01 open Assets:Checking USD\n2024-01-01 open Assets:Savings USD\n"
    "2024-01-01 open Expenses:Uncategorized USD\n2024-01-01 open Income:Gift USD\n"
)
HEAD = "Date,Description,Amount,Category,Reference\n"
CSV = "date=Date,narration=Description,amount=Amount,category=Category,id=Reference,decimal=point"


def _import(tmp_path: Path, name: str, account: str, *flags: str) -> list[str]:
    return ["import", name, "--csv", CSV, "--account", account, *flags]


def _totals(tmp_path: Path) -> dict[str, str]:
    result = _bea(tmp_path, "query", "SELECT account, sum(number) GROUP BY account ORDER BY account")
    return {account: total for account, total in json.loads(result.stdout)["data"]["rows"]}


def _book_checking(tmp_path: Path, rows: str) -> None:
    (tmp_path / "main.bean").write_text(OPENS)
    (tmp_path / "checking.csv").write_text(HEAD + rows)
    assert _written(_bea(tmp_path, *_import(tmp_path, "checking.csv", "Assets:Checking", "--apply"))) >= 1


@pytest.mark.parametrize("reverse", [False, True], ids=["staggered", "reversed"])
def test_two_transfers_pair_with_two_rows(tmp_path: Path, reverse: bool) -> None:
    _book_checking(
        tmp_path,
        "2024-02-01,TRANSFER TO SAVINGS,-100.00,Assets:Savings,C-1\n"
        "2024-02-03,TRANSFER TO SAVINGS,-100.00,Assets:Savings,C-2\n",
    )
    rows = [
        "2024-02-02,TRANSFER FROM CHECKING,100.00,Assets:Checking,S-1\n",
        "2024-02-04,TRANSFER FROM CHECKING,100.00,Assets:Checking,S-2\n",
    ]
    (tmp_path / "savings.csv").write_text(HEAD + "".join(reversed(rows) if reverse else rows))
    before = (tmp_path / "main.bean").read_bytes()

    preview = _bea(tmp_path, *_import(tmp_path, "savings.csv", "Assets:Savings"))
    data = json.loads(preview.stdout)["data"]
    assert [row["status"] for row in data["rows"]] == ["possible_duplicate", "possible_duplicate"]
    assert len({row["match"]["lineno"] for row in data["rows"]}) == 2

    applied = _bea(tmp_path, *_import(tmp_path, "savings.csv", "Assets:Savings", "--apply", "--duplicates", "skip"))
    assert _written(applied) == 0
    assert (tmp_path / "main.bean").read_bytes() == before
    assert _totals(tmp_path)["Assets:Savings"] == "200.00"


@pytest.mark.parametrize("reverse", [False, True], ids=["transfer-first", "gift-first"])
def test_a_shared_reference_keeps_its_transfer_and_the_gift_is_written(tmp_path: Path, reverse: bool) -> None:
    _book_checking(tmp_path, "2024-02-01,TRANSFER TO SAVINGS,-100.00,Assets:Savings,SHARED-1\n")
    rows = [
        "2024-02-02,TRANSFER FROM CHECKING,100.00,Assets:Checking,SHARED-1\n",
        "2024-02-01,BIRTHDAY GIFT,100.00,Income:Gift,GIFT-1\n",
    ]
    (tmp_path / "savings.csv").write_text(HEAD + "".join(reversed(rows) if reverse else rows))

    applied = _bea(tmp_path, *_import(tmp_path, "savings.csv", "Assets:Savings", "--apply", "--duplicates", "skip"))

    assert _written(applied) == 1
    assert _totals(tmp_path) == {
        "Assets:Checking": "-100.00",
        "Assets:Savings": "200.00",
        "Income:Gift": "-100.00",
    }


def test_one_transfer_still_takes_only_one_of_two_same_amount_rows(tmp_path: Path) -> None:
    """The w5/821 control: the extra deposit beside a transfer is real."""
    _book_checking(tmp_path, "2024-02-01,TRANSFER TO SAVINGS,-100.00,Assets:Savings,C-1\n")
    (tmp_path / "savings.csv").write_text(
        HEAD
        + "2024-02-02,TRANSFER FROM CHECKING,100.00,Assets:Checking,S-1\n"
        + "2024-02-02,BIRTHDAY GIFT,100.00,Income:Gift,GIFT-1\n"
    )

    applied = _bea(tmp_path, *_import(tmp_path, "savings.csv", "Assets:Savings", "--apply", "--duplicates", "skip"))

    assert _written(applied) == 1
    assert _totals(tmp_path)["Assets:Savings"] == "200.00"
