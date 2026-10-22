"""An acquisition date an importer states is part of the lot's import identity (w5/897).

Two same-day sales selecting different dated lots hashed to one ID, so the
second statement's sale, cash and gain were skipped as an exact duplicate,
even under `--duplicates include`, and holdings stayed at 3 instead of 2.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

LEDGER = (
    '2024-01-01 open Assets:Broker:HOOL HOOL "STRICT"\n'
    "2024-01-01 open Assets:Cash USD\n2024-01-01 open Income:Gains USD\n"
    '2024-01-02 * "Buy first lot"\n  Assets:Broker:HOOL 2 HOOL {100 USD}\n  Assets:Cash -200 USD\n'
    '2024-01-03 * "Buy second lot"\n  Assets:Broker:HOOL 2 HOOL {100 USD}\n  Assets:Cash -200 USD\n'
)
IMPORTER = """import datetime
from decimal import Decimal as D
from beancount.core import data, amount, position

class Imp:
    def identify(self, file):
        return str(file).endswith('.txt')
    def account(self, file):
        return 'Assets:Broker:HOOL'
    def extract(self, file, existing_entries=None):
        rows = []
        for line in open(file):
            lotdate, label = line.strip().split('|')
            cost = position.CostSpec(
                D('100'), None, 'USD', datetime.date.fromisoformat(lotdate) if lotdate else None, label or None, False)
            postings = [
                data.Posting('Assets:Broker:HOOL', amount.Amount(D('-1'), 'HOOL'), cost,
                             amount.Amount(D('150'), 'USD'), None, None),
                data.Posting('Assets:Cash', amount.Amount(D('150'), 'USD'), None, None, None, None),
                data.Posting('Income:Gains', amount.Amount(D('-50'), 'USD'), None, None, None, None),
            ]
            rows.append(data.Transaction(data.new_metadata(str(file), 1), datetime.date(2024, 2, 1), '*',
                                         'Broker', 'Sold HOOL', frozenset(), frozenset(), postings))
        return rows

CONFIG = [Imp()]
"""


def _run(name: str, *flags: str) -> list[str]:
    return ["import", name, "--config", "importers.py", "--duplicates", "include", *flags]


def _holdings(tmp_path: Path) -> Decimal:
    result = _bea(tmp_path, "query", "SELECT sum(number) WHERE account = 'Assets:Broker:HOOL'")
    return Decimal(str(json.loads(result.stdout)["data"]["rows"][0][0]))


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "statement-a.txt").write_text("2024-01-02|\n")
    (tmp_path / "statement-b.txt").write_text("2024-01-03|\n")
    return tmp_path


def test_two_statements_selecting_different_lots_both_write(books: Path) -> None:
    assert _written(_bea(books, *_run("statement-a.txt", "--apply"))) == 1

    preview = json.loads(_bea(books, *_run("statement-b.txt")).stdout)["data"]
    assert (preview["ready"], preview["duplicates"]) == (1, 0)
    assert "2024-01-03" in preview["rows"][0]["amount"]

    assert _written(_bea(books, *_run("statement-b.txt", "--apply"))) == 1
    assert _holdings(books) == 2
    assert _bea(books, "check").returncode == 0
    for name in ("statement-a.txt", "statement-b.txt"):
        assert _written(_bea(books, *_run(name, "--apply"))) == 0


def test_the_same_dated_lot_is_still_an_exact_duplicate(books: Path) -> None:
    assert _written(_bea(books, *_run("statement-a.txt", "--apply"))) == 1
    assert _written(_bea(books, *_run("statement-a.txt", "--apply"))) == 0
    assert _holdings(books) == 3


def test_an_older_dateless_id_does_not_consume_a_different_dated_lot(books: Path) -> None:
    assert _written(_bea(books, *_run("statement-a.txt", "--apply"))) == 1
    ledger = books / "main.bean"
    text = ledger.read_text()
    (found,) = re.findall(r'import-id: "(csv:sha256:[0-9a-f]+)"', text)
    # What a release before the date counted wrote for this row: the id of the date-less spelling.
    from bea_engine.importing import _digest_import_id, _hash_base

    base = _hash_base("2024-02-01", "-1 HOOL {100 USD} @ 150 USD", "SOLD HOOL", "Assets:Broker:HOOL")
    legacy = _digest_import_id(base, 1)
    ledger.write_text(text.replace(found, legacy))

    # The same dated lot still matches through the legacy id; a different dated lot does not.
    assert _written(_bea(books, *_run("statement-a.txt", "--apply"))) == 0
    assert _written(_bea(books, *_run("statement-b.txt", "--apply"))) == 1
    assert _holdings(books) == 2
