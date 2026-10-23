"""An importer returning the parser's entries may omit a counter amount or currency (w5/926).

The official parser marks an omitted amount with its `MISSING` sentinel, and a
number without a currency as an amount whose currency is that sentinel. The
first failed on the first attribute read, the second printed the sentinel's
class name as a commodity and was refused as an invalid token.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
IMPORTER = """from pathlib import Path
from beancount.parser import parser

class Imp:
    def identify(self, file): return str(file).endswith(".txt")
    def account(self, file): return "Assets:Cash"
    def extract(self, file, existing_entries=None):
        entries, errors, _ = parser.parse_string(Path(file).read_text(encoding="utf-8"))
        assert not errors, errors
        return entries

CONFIG = [Imp()]
"""
RUN = ["import", "bank.txt", "--config", "importers.py"]


def _books(tmp_path: Path, counter: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "bank.txt").write_text(
        f'2024-02-01 * "Coffee"\n  bank_id: "coffee-1"\n  Assets:Cash -4.50 USD\n  Expenses:Food{counter}\n'
    )


def _totals(tmp_path: Path) -> dict[str, Decimal]:
    result = _bea(tmp_path, "query", "SELECT account, sum(number) GROUP BY account ORDER BY account")
    return {a: Decimal(str(n)) for a, n in json.loads(result.stdout)["data"]["rows"]}


@pytest.mark.parametrize(
    "counter", ["", " 4.50", " 4.50 USD", " USD"], ids=["bare", "number-only", "explicit", "currency-only"]
)
def test_each_form_of_counter_posting_imports_and_repeats(tmp_path: Path, counter: str) -> None:
    _books(tmp_path, counter)

    preview = _bea(tmp_path, *RUN)
    assert preview.returncode == 0, preview.stderr
    assert json.loads(preview.stdout)["data"]["ready"] == 1

    assert _written(_bea(tmp_path, *RUN, "--apply")) == 1
    assert _totals(tmp_path) == {"Assets:Cash": Decimal("-4.50"), "Expenses:Food": Decimal("4.50")}
    assert _bea(tmp_path, "check").returncode == 0
    assert _written(_bea(tmp_path, *RUN, "--apply")) == 0


def test_a_stated_number_that_does_not_balance_is_still_refused(tmp_path: Path) -> None:
    _books(tmp_path, " 5.50")
    before = (tmp_path / "main.bean").read_bytes()

    refused = _bea(tmp_path, *RUN, "--apply")

    assert refused.returncode != 0
    assert (tmp_path / "main.bean").read_bytes() == before


def test_the_counter_currency_follows_the_postings_not_the_operating_currency(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "EUR"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
    )
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "bank.txt").write_text(
        '2024-02-01 * "Coffee"\n  bank_id: "coffee-1"\n  Assets:Cash -4.50 USD\n  Expenses:Food 4.50\n'
    )

    assert _written(_bea(tmp_path, *RUN, "--apply")) == 1
    assert "4.50 USD" in (tmp_path / "main.bean").read_text()
