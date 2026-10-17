"""`add transactions --partial` costs a fixed number of loads, not one per row (w5/123).

A refused batch says "Pass --partial to append the N valid rows". Following
that advice used to validate the batch one row at a time — a full staged load
per row plus a re-parse of every row accepted so far: 51 seconds for 1,000
rows on a two-line ledger. The rows the batch error names are now dropped, the
rest are confirmed with one load, and errors that cannot be placed on a row are
bisected for (w5/537).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bea_engine import managed_load, protocol
from bea_engine.ledger import adding

LEDGER = "2026-01-01 open Expenses:Food USD\n2026-01-01 open Assets:Cash USD\n"
UNKNOWN = (
    "Proposed append (not written): Invalid reference to unknown account 'Expenses:Nope' "
    "Did you mean Expenses:Food? To create it, use bea add open --account Expenses:Nope --date YYYY-MM-DD."
)


def _row(n: int, account: str = "Expenses:Food") -> dict[str, Any]:
    return {
        "date": f"2026-02-{n % 28 + 1:02d}",
        "narration": f"r{n}",
        "postings": [{"account": account, "amount": "1 USD"}, {"account": "Assets:Cash"}],
    }


def _rows(count: int, bad: set[int]) -> list[dict[str, Any]]:
    return [_row(n, "Expenses:Nope" if n in bad else "Expenses:Food") for n in range(count)]


@pytest.fixture
def loads(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    seen: list[Path] = []
    real = managed_load.load_file

    def counting(path: Any, *args: Any, **kwargs: Any) -> Any:
        seen.append(Path(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(managed_load, "load_file", counting)
    return seen


def _partial(ledger: Path, rows: list[dict[str, Any]], **options: Any) -> protocol.LedgerError:
    with pytest.raises(protocol.LedgerError) as raised:
        adding.answer(ledger, "transactions", {"rows": rows, "partial": True}, **options)
    return raised.value


@pytest.mark.parametrize("count", [10, 60])
def test_one_bad_row_costs_the_same_loads_at_any_batch_size(tmp_path: Path, loads: list[Path], count: int) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    error = _partial(ledger, _rows(count, {0}))

    # The refused batch, the confirmed remainder, and the write itself.
    assert len(loads) == 3, loads
    assert str(error) == f"Added {count - 1} of {count} transactions; 1 row was rejected."
    assert error.details == [f"Row 1: {UNKNOWN}"]
    assert error.result == {"written": count - 1, "written_rows": list(range(1, count)), "rejected_rows": [0]}
    written = ledger.read_text()
    assert written.startswith(LEDGER)
    assert "Expenses:Nope" not in written and '"r0"' not in written
    assert [f'"r{n}"' in written for n in range(1, count)] == [True] * (count - 1)


def test_all_valid_batch_is_the_control(tmp_path: Path, loads: list[Path]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = adding.answer(ledger, "transactions", {"rows": _rows(12, set()), "partial": True})

    assert result["written"] == 12 and result["rejected"] == []
    assert len(loads) == 2, loads


def test_each_rejected_row_keeps_its_own_message(tmp_path: Path, loads: list[Path]) -> None:
    """Rows sharing a problem are not merged into one "same problem on N more lines" detail."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    rows = _rows(9, {2, 5})
    rows[7]["date"] = "2025-06-01"  # before either account opens: a second kind of error

    error = _partial(ledger, rows)

    assert len(loads) == 3, loads
    assert str(error) == "Added 6 of 9 transactions; 3 rows were rejected."
    assert error.details[:2] == [f"Row 3: {UNKNOWN}", f"Row 6: {UNKNOWN}"]
    assert error.details[2].startswith("Row 8: Proposed append (not written): Invalid reference to inactive account")
    assert len(error.details) == 3
    assert error.result is not None
    assert error.result["written_rows"] == [0, 1, 3, 4, 6, 8]
    assert error.result["rejected_rows"] == [2, 5, 7]
    assert ledger.read_text().count(" * ") == 6


def test_into_and_allow_errors_stay_bounded(tmp_path: Path, loads: list[Path]) -> None:
    ledger = tmp_path / "main.bean"
    # A failing assertion the ledger already had: `--allow-errors` tolerates it.
    ledger.write_text(LEDGER + '2026-01-02 balance Assets:Cash 5 USD\ninclude "parts/2026.bean"\n')
    (tmp_path / "parts").mkdir()
    part = tmp_path / "parts" / "2026.bean"
    part.write_text("")

    sizes = []
    for count in (8, 40):
        part.write_text("")
        loads.clear()
        error = _partial(ledger, _rows(count, {3}), into=Path("parts/2026.bean"), allow_errors=True)
        sizes.append(len(loads))
        assert error.result is not None
        assert error.result["written"] == count - 1 and error.result["rejected_rows"] == [3]
        assert error.details == [f"Row 4: {UNKNOWN}"]
        assert part.read_text().count(" * ") == count - 1

    # Each `--allow-errors` validation also loads the ledger as it was.
    assert sizes[0] == sizes[1] <= 6, sizes


def test_unplaceable_errors_still_find_their_rows(tmp_path: Path, loads: list[Path]) -> None:
    """An assertion the batch breaks is reported on the ledger's own line, so no row can be named."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + "2026-03-01 balance Assets:Cash -1 ~ 1 USD\n")

    error = _partial(ledger, _rows(4, set()))

    assert error.result is not None
    assert error.result["written_rows"] == [0, 1] and error.result["rejected_rows"] == [2, 3]
    assert len(error.details) == 2 and all("Balance failed" in detail for detail in error.details)
    assert ledger.read_text().count(" * ") == 2
    assert len(loads) > 3, loads
