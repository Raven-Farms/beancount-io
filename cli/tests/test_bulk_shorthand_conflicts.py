"""A bulk `amount` that carries a cost or price cannot also take an explicit one (w5/539).

The shorthand's cost or price replaced the explicit field on the same posting
without a word, exit 0: `"amount": "5 HOOL {10 USD}"` beside
`"cost": {"number": "99", …, "label": "lot-x"}` wrote `{10 USD}`, a different
cost basis and lot.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bea_engine import protocol
from bea_engine.ledger import adding

LEDGER = "2026-01-01 open Assets:Brokerage\n2026-01-01 open Assets:Checking\n"


def _rows(amount: str, **explicit: Any) -> list[dict[str, Any]]:
    posting = {"account": "Assets:Brokerage", "amount": amount, **explicit}
    return [
        {"date": "2026-02-01", "narration": "A", "postings": [posting, {"account": "Assets:Checking"}]},
        {
            "date": "2026-02-01",
            "narration": "B",
            "postings": [{"account": "Assets:Checking", "amount": "1 USD"}, {"account": "Assets:Brokerage"}],
        },
    ]


@pytest.mark.parametrize(
    ("amount", "explicit", "detail"),
    [
        (
            "5 HOOL {10 USD}",
            {"cost": {"number": "99", "currency": "USD", "label": "lot-x"}},
            "amount '5 HOOL {10 USD}' carries a cost and the posting also gives 'cost'",
        ),
        (
            "5 HOOL @ 12 USD",
            {"price": {"number": "99", "currency": "USD"}},
            "amount '5 HOOL @ 12 USD' carries a price and the posting also gives 'price'",
        ),
        (
            "5 HOOL @@ 60 USD",
            {"price_total": {"number": "75", "currency": "USD"}},
            "amount '5 HOOL @@ 60 USD' carries a total price and the posting also gives 'price_total'",
        ),
    ],
    ids=["cost", "price", "price_total"],
)
def test_the_row_is_refused_naming_both_sources(
    tmp_path: Path, amount: str, explicit: dict[str, Any], detail: str
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    expected = f"Row 1, postings.0: Value error, {detail}; give it in one place, not both."

    with pytest.raises(protocol.LedgerError) as atomic:
        adding.answer(ledger, "transactions", {"rows": _rows(amount, **explicit)})
    assert atomic.value.details[0] == expected
    assert ledger.read_text() == LEDGER

    with pytest.raises(protocol.LedgerError) as partial:
        adding.answer(ledger, "transactions", {"rows": _rows(amount, **explicit), "partial": True})
    assert partial.value.details[0] == expected
    assert partial.value.result is not None and partial.value.result["rejected_rows"] == [0]
    assert '"A"' not in ledger.read_text() and '"B"' in ledger.read_text()


def test_a_bare_amount_still_takes_the_explicit_cost(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    adding.answer(ledger, "transactions", {"rows": _rows("5 HOOL", cost={"number": "99", "currency": "USD"})})

    assert "  Assets:Brokerage  5 HOOL {99 USD}\n" in ledger.read_text()
