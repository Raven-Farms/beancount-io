"""A lot label is written with control and bidi characters escaped, like a payee (w5/542).

Labels from broker exports or an agent's JSON were written byte for byte: an
ESC sequence or a right-to-left override right before `@ price` reached the
ledger file raw, and a newline split the posting, though payees and
narrations are escaped as `\\xNN` / `\\uNNNN` text.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from bea_engine import managed_load
from bea_engine.ledger import adding

LEDGER = "2026-01-01 open Assets:Brokerage\n2026-01-01 open Assets:Checking\n"
TYPED = "\x1b[2J‮L\nM"
# What the file holds: the visible escapes, each backslash escaped for the string.
WRITTEN = '{5 USD, "\\\\x1b[2J\\\\u202eL M"}'
READ_BACK = "\\x1b[2J\\u202eL M"


def _bulk(ledger: Path) -> None:
    cost = {"number": "5", "currency": "USD", "label": TYPED}
    posting = {"account": "Assets:Brokerage", "units": {"number": "1", "currency": "HOOL"}, "cost": cost}
    row = {"date": "2026-02-01", "narration": "buy", "postings": [posting, {"account": "Assets:Checking"}]}
    adding.answer(ledger, "transactions", {"rows": [row]})


def _single(ledger: Path) -> None:
    label = TYPED.replace("\n", " ")  # A `--posting` is one argument line.
    request = {
        "date": "2026-02-01",
        "narration": "buy",
        "postings": [f'Assets:Brokerage 1 HOOL {{5 USD, "{label}"}}', "Assets:Checking"],
    }
    adding.answer(ledger, "transaction", request)


@pytest.mark.parametrize("add", [_bulk, _single], ids=["bulk", "posting"])
def test_the_label_is_written_escaped(tmp_path: Path, add: Callable[[Path], None]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    add(ledger)

    written = ledger.read_text(encoding="utf-8")
    assert f"  Assets:Brokerage  1 HOOL {WRITTEN}\n" in written, written
    assert "\x1b" not in written and "‮" not in written
    entries, errors, _ = managed_load.load_file(ledger)
    assert errors == []
    assert [p.cost.label for e in entries if hasattr(e, "postings") for p in e.postings if p.cost] == [READ_BACK]
