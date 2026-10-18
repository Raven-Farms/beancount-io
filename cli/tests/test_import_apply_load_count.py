"""`bea import --apply` validates its candidate once (w5/577).

The preview validated the candidate, then `append` validated the same texts
against the same snapshot again under the lock: three full loads for a
one-row apply (8.7 s at 60k transactions) where `add transaction` takes one.
`append` verifies the snapshot unchanged, so the preview's answer stands.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bea_engine import importing, managed_load

LEDGER = """option "operating_currency" "USD"
2025-01-01 open Assets:Cash USD
2025-01-01 open Expenses:Food USD
2025-01-02 * "Opening"
  Assets:Cash  100.00 USD
  Expenses:Food  -100.00 USD
"""


@pytest.fixture
def loads(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    seen: list[Path] = []
    real = managed_load.load_file

    def counting(path: Any, *args: Any, **kwargs: Any) -> Any:
        seen.append(Path(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(managed_load, "load_file", counting)
    return seen


def test_a_one_row_apply_reads_once_and_validates_once(tmp_path: Path, loads: list[Path]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    source = tmp_path / "one.csv"
    source.write_text("Date,Amount,Description\n2025-01-05,-3.00,zz1\n")

    preview = importing.answer(
        ledger,
        source,
        csv_mapping="date=Date,amount=Amount,narration=Description",
        csv_account="Assets:Cash",
        default_account="Expenses:Food",
        apply=True,
    )

    assert preview["written"] == 1
    assert ledger.read_text().count('"zz1"') == 1
    # The ledger as it is, then the candidate with the row appended.
    assert len(loads) <= 2, loads
