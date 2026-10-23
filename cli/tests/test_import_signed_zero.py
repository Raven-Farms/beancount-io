"""Zero has no sign in an import amount, cost or price (w5/920).

`-0.00` rendered as `-0` while the ledger loaded it as `0`, so a zero-value row
conflicted with its own unchanged repeat (blocking the rest of an overlapping
export), and an equal `-0.00` price or cost changed the generated ID and
booked a second disposal.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

CSV_LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
CSV_RUN = [
    "import", "bank.csv", "--account", "Assets:Cash", "--default-account", "Expenses:Food",
    "--csv", "date=Date,narration=Description,amount=Amount,id=Reference,decimal=point",
]  # fmt: skip

STOCK_LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Assets:Stock HOOL "FIFO"
2024-01-01 open Equity:Opening USD
2024-01-01 open Income:Gains USD
2024-01-01 * "Capital"
  Assets:Cash 1000.00 USD
  Equity:Opening -1000.00 USD
2024-01-02 * "Buy"
  Assets:Stock 2 HOOL {COST, "Lot"}
  Assets:Cash -CASH USD
"""
IMPORTER = """import datetime, json
from decimal import Decimal as D
from pathlib import Path
from beancount.core.amount import Amount
from beancount.core.data import Transaction, Posting, new_metadata
from beancount.core.position import CostSpec

class Sales:
    def identify(self, file): return str(file).endswith('.json')
    def account(self, file): return 'Assets:Stock'
    def extract(self, file, existing_entries=None):
        row = json.loads(Path(file).read_text())
        value = D(row['value'])
        price = value if row['field'] == 'price' else D('7.00')
        cost = D('100') if row['field'] == 'price' else value
        cash = abs(price)
        meta = new_metadata(str(file), 1)
        if row['native']: meta['bank_id'] = 'disposal-1'
        return [Transaction(meta, datetime.date(2024, 2, 1), '*', None, 'Disposal', frozenset(), frozenset(), [
            Posting('Assets:Stock', Amount(D('-1'), 'HOOL'), CostSpec(cost, None, 'USD', None, 'Lot', False),
                    Amount(price, 'USD'), None, None),
            Posting('Assets:Cash', Amount(cash, 'USD'), None, None, None, None),
            Posting('Income:Gains', Amount(cost - cash, 'USD'), None, None, None, None)])]

CONFIG = [Sales()]
"""


def _csv(tmp_path: Path, *rows: str) -> None:
    (tmp_path / "main.bean").write_text(CSV_LEDGER)
    (tmp_path / "bank.csv").write_text("Date,Description,Amount,Reference\n" + "".join(rows))


def test_a_negative_zero_row_with_a_native_id_repeats_as_a_duplicate(tmp_path: Path) -> None:
    _csv(tmp_path, "2024-02-01,No charge,-0.00,zero-1\n")
    assert _written(_bea(tmp_path, *CSV_RUN, "--apply")) == 1
    first = (tmp_path / "main.bean").read_bytes()

    assert _written(_bea(tmp_path, *CSV_RUN, "--apply")) == 0
    assert (tmp_path / "main.bean").read_bytes() == first

    _csv_rows = "2024-02-01,No charge,-0.00,zero-1\n2024-02-02,Coffee,-4.50,coffee-1\n"
    (tmp_path / "bank.csv").write_text("Date,Description,Amount,Reference\n" + _csv_rows)
    assert _written(_bea(tmp_path, *CSV_RUN, "--apply")) == 1


def test_a_real_change_from_zero_is_still_a_conflict(tmp_path: Path) -> None:
    _csv(tmp_path, "2024-02-01,No charge,-0.00,zero-1\n")
    assert _written(_bea(tmp_path, *CSV_RUN, "--apply")) == 1
    (tmp_path / "bank.csv").write_text("Date,Description,Amount,Reference\n2024-02-01,No charge,-0.01,zero-1\n")

    assert _bea(tmp_path, *CSV_RUN, "--apply").returncode == 4


def _stock(tmp_path: Path, field: str, native: bool, first: str, later: str) -> tuple[Path, list[str]]:
    ledger = STOCK_LEDGER.replace("COST", "0 USD" if field == "cost" else "100 USD").replace(
        "CASH", "0.00" if field == "cost" else "200.00"
    )
    (tmp_path / "main.bean").write_text(ledger)
    (tmp_path / "importer.py").write_text(IMPORTER)
    source = tmp_path / "sale.json"
    source.write_text(json.dumps({"native": native, "field": field, "value": first}))
    return source, ["import", "sale.json", "--config", "importer.py", "--duplicates", "include", "--apply"]


def _remaining(tmp_path: Path) -> Decimal:
    result = _bea(tmp_path, "query", "SELECT sum(number) WHERE account = 'Assets:Stock'")
    return Decimal(str(json.loads(result.stdout)["data"]["rows"][0][0]))


@pytest.mark.parametrize("field", ["price", "cost"])
def test_an_equal_zero_spelling_does_not_book_a_second_disposal(tmp_path: Path, field: str) -> None:
    source, run = _stock(tmp_path, field, False, "0.00" if field == "price" else "0", "")
    assert _written(_bea(tmp_path, *run)) == 1

    source.write_text(json.dumps({"native": False, "field": field, "value": "-0.00"}))

    assert _written(_bea(tmp_path, *run)) == 0
    assert _remaining(tmp_path) == 1


def test_a_native_id_with_a_negative_zero_price_repeats_as_a_duplicate(tmp_path: Path) -> None:
    source, run = _stock(tmp_path, "price", True, "-0.00", "")
    assert _written(_bea(tmp_path, *run)) == 1

    assert _written(_bea(tmp_path, *run)) == 0
    source.write_text(json.dumps({"native": True, "field": "price", "value": "0.01"}))
    assert _bea(tmp_path, *run).returncode == 4


@pytest.mark.parametrize("field", ["price", "cost"])
def test_an_id_written_with_a_negative_zero_still_matches_the_positive_export(tmp_path: Path, field: str) -> None:
    source, run = _stock(tmp_path, field, False, "0.00" if field == "price" else "0", "")
    assert _written(_bea(tmp_path, *run)) == 1
    ledger = tmp_path / "main.bean"
    text = ledger.read_text()
    (found,) = re.findall(r'import-id: "(csv:sha256:[0-9a-f]{16})"', text)
    # The id the release before zero lost its sign wrote for a `-0.00` source.
    old = _old_negative_zero_id(tmp_path, field)
    ledger.write_text(text.replace(found, old))

    assert _written(_bea(tmp_path, *run)) == 0
    assert _remaining(tmp_path) == 1


def _old_negative_zero_id(tmp_path: Path, field: str) -> str:
    """The generated id an older release wrote, rebuilt by rendering zero with its sign."""
    import datetime

    from beancount.core.amount import Amount
    from beancount.core.data import Posting, Transaction
    from beancount.core.position import CostSpec

    from bea_engine.importing import _NEGATIVE_ZERO, _hash_import_ids

    zero = Decimal("-0.00")
    cost, price = (Decimal(100), zero) if field == "price" else (zero, Decimal("7.00"))
    leg = Posting(
        "Assets:Stock",
        Amount(Decimal(-1), "HOOL"),
        CostSpec(cost, None, "USD", None, "Lot", False),
        Amount(price, "USD"),
        None,
        None,
    )
    entry = Transaction({}, datetime.date(2024, 2, 1), "*", None, "Disposal", frozenset(), frozenset(), [leg])
    token = _NEGATIVE_ZERO.set(True)
    try:
        return _hash_import_ids(entry, "Assets:Stock", {}, raw_narration="Disposal", raw_payee=None).canonical
    finally:
        _NEGATIVE_ZERO.reset(token)
