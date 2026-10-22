"""A remembered custom date format that still reads the export is honored (w5/911).

The recall check re-inferred from the built-in list only, so `%y%m%d` on an
unchanged `240115` export was called a mismatch for `%Y%m%d`, whose advice
booked the same payments again on other dates.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

LEDGER = 'option "operating_currency" "USD"\n2020-01-01 open Assets:Cash USD\n2020-01-01 open Expenses:Food USD\n'
BASE = ["import", "bank.csv", "--account", "Assets:Cash", "--default-account", "Expenses:Food"]


def _books(tmp_path: Path, dates: list[str]) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    rows = "".join(f"{day},Coffee {index},-1.00\n" for index, day in enumerate(dates))
    (tmp_path / "bank.csv").write_text("Date,Description,Amount\n" + rows)


def _postings(tmp_path: Path) -> list[Decimal]:
    result = _bea(tmp_path, "query", "SELECT number WHERE account = 'Assets:Cash'")
    return [Decimal(str(row[0])) for row in json.loads(result.stdout)["data"]["rows"]]


@pytest.mark.parametrize(
    ("dates", "custom"),
    [
        (["240115", "240116", "240117"], "%y%m%d"),
        (["2024-05-03", "2024-06-03", "2024-07-03"], "%Y-%d-%m"),
    ],
    ids=["yymmdd", "year-day-month"],
)
def test_an_unchanged_export_repeats_with_the_remembered_format(tmp_path: Path, dates: list[str], custom: str) -> None:
    _books(tmp_path, dates)
    assert _written(_bea(tmp_path, *BASE, "--date-format", custom, "--apply")) == 3
    first = (tmp_path / "main.bean").read_bytes()

    preview = _bea(tmp_path, *BASE)
    again = _bea(tmp_path, *BASE, "--apply")

    assert preview.returncode == 0, preview.stderr
    assert json.loads(preview.stdout)["data"]["duplicates"] == 3
    assert _written(again) == 0
    assert (tmp_path / "main.bean").read_bytes() == first
    assert _postings(tmp_path) == [Decimal("-1.00")] * 3


def test_a_changed_export_is_still_refused(tmp_path: Path) -> None:
    _books(tmp_path, ["2024-01-15", "2024-01-16", "2024-01-17"])
    assert _written(_bea(tmp_path, *BASE, "--date-format", "%Y-%m-%d", "--apply")) == 3
    (tmp_path / "bank.csv").write_text(
        "Date,Description,Amount\n15/02/2024,Coffee 3,-1.00\n16/02/2024,Coffee 4,-1.00\n17/02/2024,Coffee 5,-1.00\n"
    )
    before = (tmp_path / "main.bean").read_bytes()

    refused = _bea(tmp_path, *BASE, "--apply")

    assert refused.returncode == 2, refused.stdout
    assert "does not match" in refused.stderr
    assert (tmp_path / "main.bean").read_bytes() == before
