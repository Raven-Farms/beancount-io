"""A partial cost selector picks a lot, so it is part of the import identity (w5/899).

`_lot_text` wrote a cost only when it stated both number and currency, so
same-day sales selecting `{"X"}` and `{"Y"}`, or `{100}` and `{120}`, hashed
alike and the second statement's sale was skipped as an exact duplicate.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

BASE = '2024-01-01 open Assets:Stock HOOL "FIFO"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Income:Gains USD\n'
LABELS = (
    BASE
    + '2024-01-02 * "Buy X"\n  Assets:Stock 2 HOOL {100 USD, "X"}\n  Assets:Cash -200 USD\n'
    + '2024-01-03 * "Buy Y"\n  Assets:Stock 2 HOOL {100 USD, "Y"}\n  Assets:Cash -200 USD\n'
)
NUMBERS = (
    BASE
    + '2024-01-02 * "Buy 100"\n  Assets:Stock 2 HOOL {100 USD}\n  Assets:Cash -200 USD\n'
    + '2024-01-03 * "Buy 120"\n  Assets:Stock 2 HOOL {120 USD}\n  Assets:Cash -240 USD\n'
)
IMPORTER = """from datetime import date
from decimal import Decimal as D
from beancount.core import data, amount, position
from beancount.core.number import MISSING

class Imp:
    def identify(self, file): return str(file).endswith('.txt')
    def account(self, file): return 'Assets:Stock'
    def extract(self, file, existing_entries=None):
        text = open(file).read().strip()
        {cost}
        posts = [
            data.Posting('Assets:Stock', amount.Amount(D('-1'), 'HOOL'), cost, amount.Amount(D('150'), 'USD'),
                         None, None),
            data.Posting('Assets:Cash', amount.Amount(D('150'), 'USD'), None, None, None, None),
            data.Posting('Income:Gains', None, None, None, None, None),
        ]
        return [data.Transaction(data.new_metadata(file, 1), date(2024, 2, 1), '*', 'Broker', 'Sale',
                                 frozenset(), frozenset(), posts)]

CONFIG = [Imp()]
"""
LABEL_COST = "cost = position.CostSpec(MISSING, None, None, None, text, False)"
NUMBER_COST = "cost = position.CostSpec(D(text), None, None, None, None, False)"
RUN = ["import", "{name}", "--config", "importers.py", "--duplicates", "include"]


def _run(name: str, *flags: str) -> list[str]:
    return [name if part == "{name}" else part for part in RUN] + list(flags)


def _totals(tmp_path: Path) -> dict[str, Decimal]:
    result = _bea(tmp_path, "query", "SELECT account, sum(number) GROUP BY account ORDER BY account")
    return {a: Decimal(str(n)) for a, n in json.loads(result.stdout)["data"]["rows"]}


def _books(tmp_path: Path, ledger: str, cost: str, first: str, second: str) -> None:
    (tmp_path / "main.bean").write_text(ledger)
    (tmp_path / "importers.py").write_text(IMPORTER.replace("{cost}", cost))
    (tmp_path / "sale-a.txt").write_text(first)
    (tmp_path / "sale-b.txt").write_text(second)


@pytest.mark.parametrize(
    ("ledger", "cost", "first", "second", "stock", "cash"),
    [
        (LABELS, LABEL_COST, "X", "Y", Decimal(2), Decimal(-100)),
        (NUMBERS, NUMBER_COST, "100", "120", Decimal(2), Decimal(-140)),
    ],
    ids=["labels", "numbers"],
)
def test_two_partial_selectors_are_two_sales(
    tmp_path: Path, ledger: str, cost: str, first: str, second: str, stock: Decimal, cash: Decimal
) -> None:
    _books(tmp_path, ledger, cost, first, second)

    assert _written(_bea(tmp_path, *_run("sale-a.txt", "--apply"))) == 1
    preview = json.loads(_bea(tmp_path, *_run("sale-b.txt")).stdout)["data"]
    assert (preview["ready"], preview["duplicates"]) == (1, 0)
    assert _written(_bea(tmp_path, *_run("sale-b.txt", "--apply"))) == 1

    totals = _totals(tmp_path)
    assert (totals["Assets:Stock"], totals["Assets:Cash"]) == (stock, cash)
    assert _bea(tmp_path, "check").returncode == 0
    for name in ("sale-a.txt", "sale-b.txt"):
        assert _written(_bea(tmp_path, *_run(name, "--apply"))) == 0


def test_the_same_selector_twice_is_still_a_duplicate(tmp_path: Path) -> None:
    _books(tmp_path, LABELS, LABEL_COST, "X", "X")

    assert _written(_bea(tmp_path, *_run("sale-a.txt", "--apply"))) == 1
    assert _written(_bea(tmp_path, *_run("sale-b.txt", "--apply"))) == 0
    assert _totals(tmp_path)["Assets:Stock"] == 3


def test_a_labelless_legacy_id_does_not_consume_a_different_label(tmp_path: Path) -> None:
    from bea_engine.importing import _digest_import_id, _hash_base

    _books(tmp_path, LABELS, LABEL_COST, "X", "Y")
    assert _written(_bea(tmp_path, *_run("sale-a.txt", "--apply"))) == 1
    ledger = tmp_path / "main.bean"
    text = ledger.read_text()
    import re

    (found,) = re.findall(r'import-id: "(csv:sha256:[0-9a-f]+)"', text)
    # What a release before partial selectors counted wrote: the label-less spelling.
    legacy = _digest_import_id(_hash_base("2024-02-01", "-1 HOOL @ 150 USD", "SALE", "Assets:Stock"), 1)
    ledger.write_text(text.replace(found, legacy))

    assert _written(_bea(tmp_path, *_run("sale-a.txt", "--apply"))) == 0
    assert _written(_bea(tmp_path, *_run("sale-b.txt", "--apply"))) == 1
    assert _totals(tmp_path)["Assets:Stock"] == 2
