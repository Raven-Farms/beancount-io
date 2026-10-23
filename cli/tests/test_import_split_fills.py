"""An importer's open-cost fills match the lots booking split them into (w5/896).

Each incoming fill took the first compatible booked leg, or all of them, so a
two-fill FIFO sale over three lots, and a `{"X"}` selector beside a
`{100 USD}` one, were never recognised: a hand-entered sale was written again
and a native-ID re-import conflicted with its own write.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from bea_engine.importing import _legs_agree
from tests.test_import_source_facts import _bea, _written

OPENS = (
    '2024-01-01 open Assets:Broker:HOOL HOOL "FIFO"\n2024-01-01 open Assets:Cash USD\n'
    "2024-01-01 open Income:CapitalGains USD\n"
)
BUYS = (
    '2024-01-02 * "Buy 0"\n  Assets:Broker:HOOL 2 HOOL {100 USD}\n  Assets:Cash -200 USD\n'
    '2024-01-03 * "Buy 1"\n  Assets:Broker:HOOL 2 HOOL {110 USD}\n  Assets:Cash -220 USD\n'
    '2024-01-04 * "Buy 2"\n  Assets:Broker:HOOL 16 HOOL {120 USD}\n  Assets:Cash -1920 USD\n'
)
SALE = (
    '2024-02-01 * "Sold HOOL fills"\n  Assets:Broker:HOOL -4 HOOL {} @ 150 USD\n'
    "  Assets:Broker:HOOL -6 HOOL {} @ 150 USD\n  Assets:Cash 1500 USD\n  Income:CapitalGains\n"
)
IMPORTER = """from pathlib import Path
from beancount.parser import parser

class Imp:
    def identify(self, file): return str(file).endswith(".txt")
    def account(self, file): return "{account}"
    def extract(self, file, existing_entries=None):
        entries, errors, _ = parser.parse_string(Path(file).read_text())
        assert not errors, errors
        from beancount.core.number import MISSING
        out = []
        for entry in entries:
            entry.meta["bank_id"] = "{bank_id}"
            # An elided posting parses to the MISSING sentinel; an importer says None.
            fixed = [p._replace(units=None) if p.units is MISSING else p for p in entry.postings]
            out.append(entry._replace(postings=fixed))
        return out

CONFIG = [Imp()]
"""
RUN = ["import", "statement.txt", "--config", "importers.py", "--duplicates", "skip"]


def _holdings(tmp_path: Path, account: str) -> Decimal:
    result = _bea(tmp_path, "query", f"SELECT sum(number) WHERE account = '{account}'")
    return Decimal(str(json.loads(result.stdout)["data"]["rows"][0][0]))


def _setup(tmp_path: Path, ledger: str, statement: str, account: str, bank_id: str = "") -> None:
    (tmp_path / "main.bean").write_text(ledger)
    (tmp_path / "statement.txt").write_text(statement)
    importer = IMPORTER.replace("{account}", account).replace("{bank_id}", bank_id)
    if not bank_id:
        importer = importer.replace('entry.meta["bank_id"] = ""', "pass")
    (tmp_path / "importers.py").write_text(importer)


def test_a_hand_entered_two_fill_sale_is_not_written_again(tmp_path: Path) -> None:
    _setup(tmp_path, OPENS + BUYS + SALE, SALE, "Assets:Broker:HOOL")

    applied = _bea(tmp_path, *RUN, "--apply")

    assert _written(applied) == 0
    assert (tmp_path / "main.bean").read_text().count("Sold HOOL fills") == 1
    assert _holdings(tmp_path, "Assets:Broker:HOOL") == 10


def test_a_native_id_two_fill_sale_reimports_exactly(tmp_path: Path) -> None:
    _setup(tmp_path, OPENS + BUYS, SALE, "Assets:Broker:HOOL", "QA-SALE-001")

    assert _written(_bea(tmp_path, *RUN, "--apply")) == 1
    assert _written(_bea(tmp_path, *RUN, "--apply")) == 0
    assert _holdings(tmp_path, "Assets:Broker:HOOL") == 10


def test_overlapping_lot_selectors_reimport_exactly(tmp_path: Path) -> None:
    ledger = (
        '2024-01-01 open Assets:Stock HOOL "FIFO"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Income:Gains USD\n'
        '2024-01-02 * "Buy X"\n  Assets:Stock 1 HOOL {100 USD, "X"}\n  Assets:Cash -100 USD\n'
        '2024-01-03 * "Buy Y"\n  Assets:Stock 19 HOOL {100 USD, "Y"}\n  Assets:Cash -1900 USD\n'
    )
    sale = (
        '2024-02-01 * "Sale"\n  Assets:Stock -1 HOOL {"X"} @ 150 USD\n  Assets:Stock -1 HOOL {100 USD} @ 150 USD\n'
        "  Assets:Cash 300 USD\n  Income:Gains -100 USD\n"
    )
    _setup(tmp_path, ledger, sale, "Assets:Stock", "QA-LOT-OVERLAP-001")

    assert _written(_bea(tmp_path, *RUN, "--apply")) == 1
    assert _written(_bea(tmp_path, *RUN, "--apply")) == 0
    assert _holdings(tmp_path, "Assets:Stock") == 18


def test_a_real_lot_difference_is_still_a_conflict(tmp_path: Path) -> None:
    _setup(tmp_path, OPENS + BUYS, SALE, "Assets:Broker:HOOL", "QA-SALE-001")
    assert _written(_bea(tmp_path, *RUN, "--apply")) == 1

    (tmp_path / "statement.txt").write_text(SALE.replace("-6 HOOL {}", "-7 HOOL {}"))

    assert _bea(tmp_path, *RUN, "--apply").returncode == 4


@pytest.mark.parametrize(
    ("ours", "theirs", "agree"),
    [
        (
            [("-4 HOOL @ 150 USD", (None, None, None), ""), ("-6 HOOL @ 150 USD", (None, None, None), "")],
            [
                ("-2 HOOL @ 150 USD", (Decimal(100), "USD", None), ""),
                ("-2 HOOL @ 150 USD", (Decimal(110), "USD", None), ""),
                ("-6 HOOL @ 150 USD", (Decimal(120), "USD", None), ""),
            ],
            True,
        ),
        (
            [("-4 HOOL @ 150 USD", (None, None, None), "")],
            [
                ("-2 HOOL @ 150 USD", (Decimal(100), "USD", None), ""),
                ("-3 HOOL @ 150 USD", (Decimal(110), "USD", None), ""),
            ],
            False,
        ),
        (
            [("-1 HOOL", (None, None, "X"), ""), ("-1 HOOL", (Decimal(100), "USD", None), "")],
            [("-1 HOOL", (Decimal(100), "USD", "X"), ""), ("-1 HOOL", (Decimal(100), "USD", "Y"), "")],
            True,
        ),
        ([("-1 HOOL", (None, None, "Z"), "")], [("-1 HOOL", (Decimal(100), "USD", "X"), "")], False),
    ],
    ids=["two-fills-three-lots", "units-do-not-add-up", "overlapping-selectors", "label-differs"],
)
def test_the_assignment_is_one_to_one(ours: list, theirs: list, agree: bool) -> None:  # type: ignore[type-arg]
    assert _legs_agree(ours, theirs) is agree
