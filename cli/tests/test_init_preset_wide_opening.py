"""A wide preset opening balance gets its exact equity offset (w5/901).

`-amount` applied the default 28-digit context, so the offset of a 29-digit
negative opening was written rounded while the asset leg kept every digit.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_init_preset import _bea

WIDE = "-12345678901.123456789012345678"


@pytest.mark.parametrize(("preset", "account"), [("personal@1", "Assets:Cash"), ("freelance@1", "Assets:Bank")])
def test_the_equity_offset_keeps_every_digit(tmp_path: Path, preset: str, account: str) -> None:
    books = tmp_path / "books"
    created = _bea(
        tmp_path, "--json", "init", str(books), "--preset", preset, "--currency", "USD", "--date", "2024-02-01",
        "--opening-balance", f"{account} {WIDE}",
    )  # fmt: skip
    assert created.returncode == 0, created.stderr or created.stdout

    text = (books / "main.bean").read_text()
    assert re.search(rf"^  {re.escape(account)} +{re.escape(WIDE)} USD$", text, re.M)
    assert re.search(rf"^  Equity:OpeningBalances +{re.escape(WIDE[1:])} USD$", text, re.M)
    assert _bea(tmp_path, "--json", "--file", str(books / "main.bean"), "check").returncode == 0
    equity = _bea(
        tmp_path,
        "--json",
        "--file",
        str(books / "main.bean"),
        "query",
        "SELECT number WHERE account = 'Equity:OpeningBalances'",
    )
    assert Decimal(str(json.loads(equity.stdout)["data"]["rows"][0][0])).copy_abs() > 0


@pytest.mark.parametrize("amount", ["1234567890.123456789012345678", "-1234567890.123456789012345678"])
def test_a_28_digit_opening_of_either_sign_is_exact(tmp_path: Path, amount: str) -> None:
    books = tmp_path / "books"
    created = _bea(
        tmp_path, "--json", "init", str(books), "--preset", "personal@1", "--currency", "USD", "--date", "2024-02-01",
        "--opening-balance", f"Assets:Cash {amount}",
    )  # fmt: skip
    assert created.returncode == 0, created.stderr or created.stdout

    negated = amount[1:] if amount.startswith("-") else f"-{amount}"
    text = (books / "main.bean").read_text()
    assert re.search(rf"^  Equity:OpeningBalances +{re.escape(negated)} USD$", text, re.M)
    assert _bea(tmp_path, "--json", "--file", str(books / "main.bean"), "check").returncode == 0
