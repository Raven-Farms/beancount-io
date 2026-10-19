"""`add transactions --partial` drops named rows before bisecting, and judges dense remainders in order (w5/720).

w5/537 bisects for the rows an existing balance assertion refuses, which made
the single-bad-row case fast but batches with many bad rows slower: one
unplaceable error discarded every row the batch error did name, and each
remaining bad row cost a fresh bisection over the whole rest of the batch —
932 loads for a 400-row monthly bulk add with a few typos and an
assertion-breaking row, against 401 before. Named rows are now dropped first
and only the unplaceable remainder is bisected; once bisection has spent past
one round's worth of loads beyond the rows it decided, the rest are judged in
order. The scan keeps every leading run that loads and refuses the row that
breaks it, so a kept row can fail alone when a later kept row offsets it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bea_engine import protocol
from bea_engine.ledger import adding, write

LEDGER = (
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Assets:Cash USD\n"
    "2026-01-01 open Expenses:Food USD\n"
    "2026-12-31 balance Assets:Checking 0 USD\n"
)

BALANCED = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Assets:Cash\n"
    "2026-01-01 open Expenses:Food\n"
    "2026-12-31 balance Assets:Checking 0 USD\n"
)


@pytest.fixture
def validates(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Ledger loads (`write.validate_append` calls), the unit w5/720 counts in."""
    seen: list[int] = []
    real = write.validate_append

    def counting(*args: Any, **kwargs: Any) -> Any:
        seen.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(write, "validate_append", counting)
    return seen


def _partial(ledger: Path, rows: list[dict[str, Any]]) -> protocol.LedgerError:
    with pytest.raises(protocol.LedgerError) as raised:
        adding.answer(ledger, "transactions", {"rows": rows, "partial": True})
    return raised.value


def _rows(count: int, bad: set[int], nope: set[int] = frozenset()) -> list[dict[str, Any]]:
    """Rows paying for food in cash; a bad row pays from the asserted checking, a nope row names an unopened account."""
    return [
        {
            "date": "2026-02-01",
            "narration": f"r{n}",
            "postings": [
                {"account": "Expenses:Nope" if n in nope else "Expenses:Food", "amount": "1 USD"},
                {"account": "Assets:Checking" if n in bad else "Assets:Cash"},
            ],
        }
        for n in range(count)
    ]


def test_every_other_row_bad_stays_within_twice_the_per_row_budget(tmp_path: Path, validates: list[int]) -> None:
    """At k/n = 1/2 bisection costs more per row than judging in order, so the remainder goes row by row."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    count = 60

    error = _partial(ledger, _rows(count, set(range(0, count, 2))))

    assert str(error) == f"Added {count // 2} of {count} transactions; {count // 2} rows were rejected."
    assert error.result is not None and error.result["rejected_rows"] == list(range(0, count, 2))
    assert ledger.read_text().count(" * ") == count // 2
    # A trial per row costs count + 1 loads; pure bisection cost over 200.
    assert len(validates) <= 2 * count, len(validates)


def test_mixed_named_and_assertion_rows_drop_then_bisect(tmp_path: Path, validates: list[int]) -> None:
    """Rows the batch error names are refused with their own lines; only the assertion remainder is searched."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    bad = {n for n in range(60) if n % 6 == 5}
    nope = {n for n in range(60) if n % 7 == 3}

    error = _partial(ledger, _rows(60, bad, nope))

    assert error.result is not None
    assert error.result["rejected_rows"] == [3, 5, 10, 11, 17, 23, 24, 29, 31, 35, 38, 41, 45, 47, 52, 53, 59]
    assert str(error) == "Added 43 of 60 transactions; 17 rows were rejected."
    assert len(error.details) == 17
    for detail in error.details:
        row = int(detail.split(":")[0].split()[1]) - 1
        if row in nope:
            assert "Expenses:Nope" in detail
        else:
            assert "Balance failed" in detail
    assert ledger.read_text().count(" * ") == 43
    # Dropping the named rows first beats the per-row budget of 61; bisecting everything cost 97.
    assert len(validates) <= 61, len(validates)


def test_mixed400_beats_the_pre_fix_per_row_loads(tmp_path: Path, validates: list[int]) -> None:
    """The note's monthly bulk add: 400 rows with typos and assertion breakers cost under 400 loads."""
    ledger = tmp_path / "bal.bean"
    ledger.write_text(BALANCED)
    rows: list[dict[str, Any]] = []
    for i in range(400):
        if i % 10 == 5:
            postings = [{"account": "Assets:Checking", "amount": "1 USD"}, {"account": "Assets:Cash"}]
        elif i % 7 == 3:
            postings = [{"account": "Expenses:Nope", "amount": "1 USD"}, {"account": "Assets:Cash"}]
        elif i % 13 == 4:
            postings = [{"account": "Assets:Checking", "amount": "1 EUR"}, {"account": "Assets:Cash"}]
        else:
            postings = [{"account": "Expenses:Food", "amount": "1 USD"}, {"account": "Assets:Cash"}]
        rows.append({"date": "2026-02-01", "narration": f"r{i}", "postings": postings})

    error = _partial(ledger, rows)

    assert str(error) == "Added 286 of 400 transactions; 114 rows were rejected."
    assert error.result is not None and len(error.result["rejected_rows"]) == 114
    assert ledger.read_text().count(" * ") == 286
    # The pre-fix per-row fallback cost 401 loads; HEAD's bisect-everything cost over 900.
    assert len(validates) < 400, len(validates)


def test_forward_scan_keeps_a_row_a_later_row_offsets(tmp_path: Path) -> None:
    """The keep rule bisection implements: every leading run that loads is kept, the row breaking it refused.

    Row 1 alone breaks the checking assertion, but row 2 offsets it, so the
    scan keeps rows 1-3 and refuses row 4. Which rows are kept is
    deterministic for a given row order — reordering refuses a different row.
    """
    base = (
        "2026-01-01 open Assets:Checking USD\n"
        "2026-01-01 open Assets:Cash USD\n"
        "2026-01-01 open Expenses:Food USD\n"
        "2026-01-01 open Income:Salary USD\n"
        "2026-12-31 balance Assets:Checking 0 USD\n"
    )

    def row(narration: str, postings: list[dict[str, str]]) -> dict[str, Any]:
        return {"date": "2026-02-01", "narration": narration, "postings": postings}

    first = row("r1", [{"account": "Assets:Checking", "amount": "1 USD"}, {"account": "Income:Salary"}])
    second = row("r2", [{"account": "Expenses:Food", "amount": "1 USD"}, {"account": "Assets:Checking"}])
    third = row("r3", [{"account": "Expenses:Food", "amount": "1 USD"}, {"account": "Assets:Cash"}])
    fourth = row("r4", [{"account": "Assets:Checking", "amount": "1 USD"}, {"account": "Income:Salary"}])

    ledger = tmp_path / "main.bean"
    ledger.write_text(base)
    error = _partial(ledger, [first, second, third, fourth])
    assert str(error) == "Added 3 of 4 transactions; 1 row was rejected."
    assert error.result is not None and error.result["written_rows"] == [0, 1, 2]
    assert error.result["rejected_rows"] == [3]
    assert len(error.details) == 1 and error.details[0].startswith("Row 4: ")

    ledger.write_text(base)
    error = _partial(ledger, [fourth, first, second, third])
    assert str(error) == "Added 3 of 4 transactions; 1 row was rejected."
    assert error.result is not None and error.result["written_rows"] == [1, 2, 3]
    assert error.result["rejected_rows"] == [0]
    assert len(error.details) == 1 and error.details[0].startswith("Row 1: ")
