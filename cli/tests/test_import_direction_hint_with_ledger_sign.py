"""The unmapped-direction refusal gives a repair that runs when `sign=ledger` is active (w5/918).

It said to add `direction=Type`, which the parser refuses beside `sign=ledger`,
so following the hint produced a second refusal; the repair is a replacement.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_import_source_facts import _bea, _written

LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
BASE = ["import", "bank.csv", "--account", "Assets:Cash", "--default-account", "Expenses:Food"]
MAPPING = "date=Date,narration=Description,amount=Amount"


def _books(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_text("Date,Description,Amount,Type\n2024-02-01,Coffee,4.50,DEBIT\n")


def _message(result: object) -> str:
    return " ".join(json.loads(result.stderr)["error"]["message"].split())  # type: ignore[attr-defined]


def test_the_hint_is_a_replacement_and_following_it_works(tmp_path: Path) -> None:
    _books(tmp_path)
    before = (tmp_path / "main.bean").read_bytes()

    refused = _bea(tmp_path, *BASE, "--csv", f"{MAPPING},sign=ledger")

    assert refused.returncode == 2, refused.stdout
    message = _message(refused)
    assert "Replace sign=ledger with direction=Type" in message
    assert "money in" not in message and "Add direction=Type" not in message
    assert (tmp_path / "main.bean").read_bytes() == before

    repaired = _bea(tmp_path, *BASE, "--csv", f"{MAPPING},direction=Type", "--apply")
    assert _written(repaired) == 1
    assert "Assets:Cash" in (tmp_path / "main.bean").read_text()
    assert "-4.50 USD" in (tmp_path / "main.bean").read_text()


def test_without_sign_ledger_the_ordinary_hint_is_unchanged(tmp_path: Path) -> None:
    _books(tmp_path)

    refused = _bea(tmp_path, *BASE, "--csv", MAPPING)

    assert refused.returncode == 2, refused.stdout
    message = _message(refused)
    assert "Add direction=Type to the --csv mapping" in message and "every debit would book as money in" in message
