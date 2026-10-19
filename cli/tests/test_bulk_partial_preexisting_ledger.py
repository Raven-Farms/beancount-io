"""A batch that adds nothing wrong to already-broken books blames no row (w5/725).

The atomic refusal advised `--partial`, and `--partial` then rejected every
row with the pre-existing error repeated per row. Now the atomic refusal
offers only `--allow-errors`, and `--partial` reports the ledger's failure
once. A batch that adds its own errors to broken books still judges each row
(w5/537's per-row guard).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bea_engine import managed_load, protocol
from bea_engine.ledger import adding

LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Assets:Cash\n"
    "2026-01-01 open Expenses:Food\n"
    "2026-12-31 balance Assets:Checking 5 USD\n"
)


def _rows(count: int) -> list[Any]:
    """Valid rows; none touches the asserted checking account."""
    return [
        {
            "date": "2026-02-01",
            "narration": f"r{n}",
            "postings": [
                {"account": "Expenses:Food", "amount": "1 USD"},
                {"account": "Assets:Cash"},
            ],
        }
        for n in range(count)
    ]


@pytest.fixture
def loads(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    seen: list[Path] = []
    real = managed_load.load_file

    def counting(path: Any, *args: Any, **kwargs: Any) -> Any:
        seen.append(Path(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(managed_load, "load_file", counting)
    return seen


def test_atomic_refusal_offers_only_allow_errors(tmp_path: Path) -> None:
    ledger = tmp_path / "err.bean"
    ledger.write_text(LEDGER)

    with pytest.raises(protocol.LedgerError) as raised:
        adding.answer(ledger, "transactions", {"rows": _rows(5)})

    error = raised.value
    assert str(error).startswith("The ledger already has 1 error(s); nothing was written.")
    assert "--allow-errors" in str(error)
    assert "--partial" not in str(error)
    assert error.result == {"written": 0, "written_rows": [], "unwritten_rows": [0, 1, 2, 3, 4]}
    assert ledger.read_text().count(" * ") == 0


def test_partial_reports_the_ledger_failure_once(tmp_path: Path, loads: list[Path]) -> None:
    ledger = tmp_path / "err.bean"
    ledger.write_text(LEDGER)
    loads.clear()

    with pytest.raises(protocol.LedgerError) as raised:
        adding.answer(ledger, "transactions", {"rows": _rows(5), "partial": True})

    error = raised.value
    assert str(error).startswith("The ledger already has 1 error(s); nothing was written.")
    assert [detail.startswith("Row ") for detail in error.details] == [False] * len(error.details)
    assert any("Balance failed for 'Assets:Checking'" in detail for detail in error.details)
    assert error.result == {"written": 0, "written_rows": [], "rejected_rows": [0, 1, 2, 3, 4]}
    assert ledger.read_text().count(" * ") == 0
    # The refused batch plus the before-version it was compared against; no row is judged.
    assert len(loads) <= 4, len(loads)


def test_schema_rejections_stay_row_blamed(tmp_path: Path) -> None:
    """Rows invalid on their own keep their own lines; only the ledger failure is the ledger's."""
    ledger = tmp_path / "err.bean"
    ledger.write_text(LEDGER)
    rows = _rows(5)
    rows[2] = "oops"

    with pytest.raises(protocol.LedgerError) as raised:
        adding.answer(ledger, "transactions", {"rows": rows, "partial": True})

    error = raised.value
    assert str(error).startswith("The ledger already has 1 error(s); nothing was written.")
    assert len(error.details) == 2 + 2
    assert error.details[0].startswith("Row 3, transaction: ")
    assert error.result is not None and error.result["rejected_rows"] == [2, 0, 1, 3, 4]
