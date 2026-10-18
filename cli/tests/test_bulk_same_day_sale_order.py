"""A same-day sale listed before its purchase books against it (w5/543).

Beancount books one date's entries in file order, and bulk add appended rows
in input order, so a broker export or a newest-first listing that put the
sale first found no lot: refused with `{}` ("Too many missing numbers"),
booked silently as a short position with an explicit cost.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bea_engine import managed_load, protocol
from bea_engine.ledger import adding

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Brokerage "FIFO"
2026-01-01 open Income:Gains USD
"""
DEPOSIT = {
    "date": "2026-01-02",
    "narration": "deposit",
    "postings": [{"account": "Assets:Checking", "amount": "1000 USD"}, {"account": "Income:Gains"}],
}
BUY = {
    "date": "2026-03-05",
    "narration": "buy",
    "postings": [
        {
            "account": "Assets:Brokerage",
            "units": {"number": "10", "currency": "HOOL"},
            "cost": {"number": "50", "currency": "USD"},
        },
        {"account": "Assets:Checking", "amount": "-500 USD"},
    ],
}
LATER = {
    "date": "2026-03-07",
    "narration": "later",
    "postings": [{"account": "Assets:Checking", "amount": "-1 USD"}, {"account": "Income:Gains"}],
}


def _sale(cost: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": "2026-03-05",
        "narration": "sell",
        "postings": [
            {
                "account": "Assets:Brokerage",
                "units": {"number": "-10", "currency": "HOOL"},
                "cost": cost,
                "price": {"number": "55", "currency": "USD"},
            },
            {"account": "Assets:Checking", "amount": "550 USD"},
            {"account": "Income:Gains"},
        ],
    }


@pytest.mark.parametrize("cost", [{}, {"number": "50", "currency": "USD"}], ids=["any-lot", "explicit-lot"])
def test_the_sale_is_written_after_the_same_day_purchase(tmp_path: Path, cost: dict[str, Any]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = adding.answer(ledger, "transactions", {"rows": [DEPOSIT, LATER, _sale(cost), BUY]})

    assert result["written"] == 4 and result["rejected"] == []
    written = ledger.read_text()
    # The date's slots stay where they were; within them the purchase comes first.
    order = [written.index(f'"{name}"') for name in ("deposit", "later", "buy", "sell")]
    assert order == sorted(order), written
    entries, errors, _ = managed_load.load_file(ledger)
    assert errors == []
    sale = next(entry for entry in entries if getattr(entry, "narration", None) == "sell")
    # Booked as a reduction of the lot bought that day, not a short position.
    assert sale.postings[0].cost.number == 50
    gains = [
        posting.units.number
        for entry in entries
        if hasattr(entry, "postings")
        for posting in entry.postings
        if posting.account == "Income:Gains" and getattr(entry, "narration", None) == "sell"
    ]
    assert gains == [-50]
    balances = [
        posting
        for entry in entries
        if hasattr(entry, "postings")
        for posting in entry.postings
        if posting.account == "Assets:Brokerage"
    ]
    assert sum(posting.units.number for posting in balances) == 0


def test_rows_without_a_same_day_purchase_keep_their_order(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    sale = {**_sale({}), "date": "2026-03-06"}

    adding.answer(ledger, "transactions", {"rows": [DEPOSIT, sale, LATER, BUY]})

    written = ledger.read_text()
    order = [written.index(f'"{name}"') for name in ("deposit", "sell", "later", "buy")]
    assert order == sorted(order), written


def test_a_partial_write_reports_rows_by_input_index(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    bad = {
        **LATER,
        "narration": "bad",
        "postings": [{"account": "Expenses:Nope", "amount": "1 USD"}, {"account": "Assets:Checking"}],
    }

    with pytest.raises(protocol.LedgerError) as raised:
        adding.answer(ledger, "transactions", {"rows": [DEPOSIT, _sale({}), BUY, bad], "partial": True})

    assert raised.value.result == {"written": 3, "written_rows": [0, 1, 2], "rejected_rows": [3]}
    assert raised.value.details[0].startswith("Row 4: ")
