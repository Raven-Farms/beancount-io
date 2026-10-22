"""A positive cover keeps the label of the short lot it covers (w5/925).

Only a negative quantity was treated as a lot reduction, so a cover's
multiline selector was flattened to `First Lot` and booked against the other,
space-labelled short lot: the gain read 30 USD instead of 10, exit 0.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from tests.test_import_source_facts import _bea

LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Stock HOOL "FIFO"
2024-01-01 open Assets:Cash USD
2024-01-01 open Income:Gains USD
2024-01-02 * "First short lot"
  Assets:Stock -2 HOOL {100 USD, "First
Lot"}
  Assets:Cash 200.00 USD
2024-01-03 * "Second short lot"
  Assets:Stock -2 HOOL {120 USD, "First Lot"}
  Assets:Cash 240.00 USD
"""
COVER = [
    {
        "date": "2024-02-01",
        "narration": "Cover first short lot",
        "postings": [
            {"account": "Assets:Stock", "units": {"number": "1", "currency": "HOOL"}, "cost": {"label": "First\nLot"}},
            {"account": "Assets:Cash", "units": {"number": "-90.00", "currency": "USD"}},
            {"account": "Income:Gains"},
        ],
    }
]


def _gains(tmp_path: Path) -> Decimal:
    result = _bea(tmp_path, "query", "SELECT sum(number) WHERE account = 'Income:Gains'")
    return Decimal(str(json.loads(result.stdout)["data"]["rows"][0][0]))


def _cover(tmp_path: Path, ledger: str) -> object:
    (tmp_path / "main.bean").write_text(ledger)
    (tmp_path / "cover.json").write_text(json.dumps(COVER))
    return _bea(tmp_path, "add", "transactions", "--from", str(tmp_path / "cover.json"))


def test_the_cover_selects_the_lot_it_names(tmp_path: Path) -> None:
    added = _cover(tmp_path, LEDGER)

    assert added.returncode == 0, added.stderr  # type: ignore[attr-defined]
    assert _gains(tmp_path) == Decimal("-10.00")
    assert _bea(tmp_path, "check").returncode == 0
    written = (tmp_path / "main.bean").read_text().split("Cover first short lot")[1]
    assert '{"First\nLot"}' in written


def test_the_valid_cover_succeeds_with_no_space_labelled_sibling(tmp_path: Path) -> None:
    only_first = LEDGER.split('2024-01-03 * "Second short lot"')[0]

    added = _cover(tmp_path, only_first)

    assert added.returncode == 0, added.stderr  # type: ignore[attr-defined]
    assert _gains(tmp_path) == Decimal("-10.00")


def test_a_new_long_buy_still_normalizes_its_label(tmp_path: Path) -> None:
    buy = [
        {
            "date": "2024-02-01",
            "narration": "Buy",
            "postings": [
                {
                    "account": "Assets:Stock",
                    "units": {"number": "1", "currency": "HOOL"},
                    "cost": {"number": "50", "currency": "USD", "label": "New\nLabel"},
                },
                {"account": "Assets:Cash", "units": {"number": "-50.00", "currency": "USD"}},
            ],
        }
    ]
    (tmp_path / "main.bean").write_text(LEDGER.split('2024-01-02 * "First short lot"')[0])
    (tmp_path / "buy.json").write_text(json.dumps(buy))

    added = _bea(tmp_path, "add", "transactions", "--from", str(tmp_path / "buy.json"))

    assert added.returncode == 0, added.stderr
    assert "New Label" in (tmp_path / "main.bean").read_text()
    assert "New\nLabel" not in (tmp_path / "main.bean").read_text()


IMPORTER = """import datetime
from decimal import Decimal as D
from beancount.core.amount import Amount
from beancount.core.data import Posting, Transaction
from beancount.core.position import CostSpec

class Imp:
    def identify(self, file): return str(file).endswith(".txt")
    def account(self, file): return "Assets:Stock"
    def extract(self, file, existing_entries=None):
        label = "First\\nLot"
        legs = [
            Posting("Assets:Stock", Amount(D("1"), "HOOL"), CostSpec(None, None, None, None, label, False),
                    None, None, None),
            Posting("Assets:Cash", Amount(D("-90.00"), "USD"), None, None, None, None),
            Posting("Income:Gains", None, None, None, None, None),
        ]
        return [Transaction({}, datetime.date(2024, 2, 1), "*", None, "Cover first short lot",
                            frozenset(), frozenset(), legs)]

CONFIG = [Imp()]
"""


def test_an_importer_cover_selects_the_same_lot(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "cover.txt").write_text("synthetic\n")

    applied = _bea(tmp_path, "import", "cover.txt", "--config", "importers.py", "--apply")

    assert applied.returncode == 0, applied.stderr
    assert _gains(tmp_path) == Decimal("-10.00")
