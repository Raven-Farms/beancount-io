"""A staged copy the disk will not take is not a validation failure (w5/607).

w5/410 gave staging I/O failures one sentence, "Cannot write a staged copy
… nothing was written". Bulk add and import read every `LedgerError` from
validation as rows the ledger refused, so a full disk came back as "Pass
--partial", every row "rejected" under `--partial`, and an import that
"would leave the ledger invalid". Here the staged copy's `fsync` answers
`EFBIG`, as under `ulimit -f`.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path
from typing import Any

import pytest

from bea_engine import importing, protocol
from bea_engine.ledger import adding

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
"""
ROWS: list[dict[str, Any]] = [
    {
        "date": "2026-02-0" + str(day),
        "narration": f"Lunch {day}",
        "postings": [{"account": "Expenses:Food", "amount": "9 USD"}, {"account": "Assets:Checking"}],
    }
    for day in (1, 2)
]
STAGING = "Cannot write a staged copy of main.bean in {directory} (File too large); nothing was written."


@pytest.fixture
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)

    def full(fd: int) -> None:
        raise OSError(errno.EFBIG, os.strerror(errno.EFBIG))

    monkeypatch.setattr(os, "fsync", full)
    return path


@pytest.mark.parametrize("partial", [False, True], ids=["all-or-nothing", "partial"])
def test_bulk_add_says_only_that_the_copy_could_not_be_written(ledger: Path, partial: bool) -> None:
    with pytest.raises(protocol.StagingFailed) as raised:
        adding._transactions(
            ledger, {"rows": ROWS, "partial": partial}, into=None, allow_errors=False, strict_read=False
        )

    assert str(raised.value) == STAGING.format(directory=ledger.parent)
    assert raised.value.result is None
    assert ledger.read_text() == LEDGER


def test_import_apply_says_only_that_the_copy_could_not_be_written(ledger: Path) -> None:
    source = ledger.parent / "bank.csv"
    source.write_text("Date,Description,Amount\n2026-02-01,Lunch,-9.00\n2026-02-02,Dinner,-12.00\n")

    with pytest.raises(protocol.StagingFailed) as raised:
        importing.answer(
            ledger,
            source,
            csv_mapping="date=Date,narration=Description,amount=Amount",
            csv_account="Assets:Checking",
            default_account="Expenses:Food",
            apply=True,
        )

    assert str(raised.value) == STAGING.format(directory=ledger.parent)
    assert ledger.read_text() == LEDGER


def test_it_keeps_the_validation_category(ledger: Path) -> None:
    assert (protocol.StagingFailed.category, protocol.StagingFailed.exit_code) == (
        protocol.LedgerError.category,
        protocol.LedgerError.exit_code,
    )
    assert not issubclass(protocol.StagingFailed, protocol.LedgerError)
