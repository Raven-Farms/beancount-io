"""A same-day sale that books in input order keeps it (w5/730).

w5/543 moved every same-day sale after every same-day purchase, so a sale
that already booked — against a lot the ledger holds, or a lot an earlier
row bought — was moved after an unrelated rebuy: refused as "Ambiguous"
under STRICT, or written after the rebuy under LIFO/FIFO, closing the
wrong lot and changing the realized gain. Only a sale with no position to
book against moves now.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bea_engine import managed_load
from bea_engine.ledger import adding

HOLDING = """2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Brokerage{booking}
2026-01-01 open Income:Gains USD
2026-01-01 open Equity:Opening
2026-01-02 * "Deposit"
  Assets:Checking  10000 USD
  Equity:Opening
2026-01-10 * "Buy Jan"
  Assets:Brokerage  10 HOOL {{40 USD}}
  Assets:Checking  -400 USD
"""
SALE = {
    "date": "2026-03-05",
    "narration": "Sell all",
    "postings": [
        {
            "account": "Assets:Brokerage",
            "units": {"number": "-10", "currency": "HOOL"},
            "cost": {},
            "price": {"number": "55", "currency": "USD"},
        },
        {"account": "Assets:Checking", "amount": "550 USD"},
        {"account": "Income:Gains"},
    ],
}
REBUY = {
    "date": "2026-03-05",
    "narration": "Rebuy",
    "postings": [
        {
            "account": "Assets:Brokerage",
            "units": {"number": "10", "currency": "HOOL"},
            "cost": {"number": "50", "currency": "USD"},
        },
        {"account": "Assets:Checking", "amount": "-500 USD"},
    ],
}


def _gains(entries: list[Any]) -> Any:
    return sum(
        posting.units.number
        for entry in entries
        if hasattr(entry, "postings")
        for posting in entry.postings
        if posting.account == "Income:Gains"
    )


@pytest.mark.parametrize("booking", ["", ' "LIFO"', ' "FIFO"'], ids=["strict", "lifo", "fifo"])
@pytest.mark.parametrize("partial", [False, True], ids=["strict-mode", "partial"])
def test_a_sale_against_a_held_lot_keeps_input_order(tmp_path: Path, booking: str, partial: bool) -> None:
    ledger = tmp_path / "hold.bean"
    ledger.write_text('option "operating_currency" "USD"\n' + HOLDING.format(booking=booking))

    result = adding.answer(ledger, "transactions", {"rows": [SALE, REBUY], "partial": partial})

    assert result["written"] == 2 and result["rejected"] == []
    written = ledger.read_text()
    assert written.index('"Sell all"') < written.index('"Rebuy"'), written
    entries, errors, _ = managed_load.load_file(ledger)
    assert errors == []
    sale = next(entry for entry in entries if getattr(entry, "narration", None) == "Sell all")
    # Closes the January lot, not the rebuy: the gain is -150 USD and the
    # 50 USD lot stays open.
    assert sale.postings[0].cost.number == 40
    assert _gains(entries) == -150
    lots = [
        (posting.units.number, posting.cost.number)
        for entry in entries
        if hasattr(entry, "postings")
        for posting in entry.postings
        if posting.account == "Assets:Brokerage" and posting.cost is not None
    ]
    assert lots == [(10, 40), (-10, 40), (10, 50)]


def test_an_explicit_cost_sale_against_a_held_lot_keeps_input_order(tmp_path: Path) -> None:
    ledger = tmp_path / "hold.bean"
    ledger.write_text('option "operating_currency" "USD"\n' + HOLDING.format(booking=""))
    sale = {
        **SALE,
        "postings": [
            {**SALE["postings"][0], "cost": {"number": "40", "currency": "USD"}},
            *SALE["postings"][1:],
        ],
    }

    result = adding.answer(ledger, "transactions", {"rows": [sale, REBUY]})

    assert result["written"] == 2 and result["rejected"] == []
    written = ledger.read_text()
    assert written.index('"Sell all"') < written.index('"Rebuy"'), written
    entries, errors, _ = managed_load.load_file(ledger)
    assert errors == []
    assert _gains(entries) == -150


def test_a_sale_after_an_earlier_same_day_buy_keeps_input_order(tmp_path: Path) -> None:
    ledger = tmp_path / "day.bean"
    ledger.write_text(
        'option "operating_currency" "USD"\n'
        "2026-01-01 open Assets:Checking USD\n"
        "2026-01-01 open Assets:Brokerage\n"
        "2026-01-01 open Income:Gains USD\n"
        "2026-01-01 open Equity:Opening\n"
        '2026-01-02 * "Deposit"\n'
        "  Assets:Checking  10000 USD\n"
        "  Equity:Opening\n"
    )
    morning = {
        "date": "2026-03-05",
        "narration": "Buy morning",
        "postings": [
            {
                "account": "Assets:Brokerage",
                "units": {"number": "10", "currency": "HOOL"},
                "cost": {"number": "40", "currency": "USD"},
            },
            {"account": "Assets:Checking", "amount": "-400 USD"},
        ],
    }
    noon = {**SALE, "narration": "Sell noon"}
    afternoon = {**REBUY, "narration": "Buy afternoon"}

    result = adding.answer(ledger, "transactions", {"rows": [morning, noon, afternoon]})

    assert result["written"] == 3 and result["rejected"] == []
    written = ledger.read_text()
    order = [written.index(f'"{name}"') for name in ("Buy morning", "Sell noon", "Buy afternoon")]
    assert order == sorted(order), written
    entries, errors, _ = managed_load.load_file(ledger)
    assert errors == []
    assert _gains(entries) == -150
