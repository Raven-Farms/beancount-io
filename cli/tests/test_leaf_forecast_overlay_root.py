"""A forecast view over the working ledger is not a second root for its leaf (w5/933).

`write_through_root` started a climb from every ancestor the include scan
found, so `forecast.bean` (which includes `main.bean`, which includes the
leaf) saw the working ledger's opens in its closure and counted as a
defining root of its own: an import or note aimed at the leaf was refused as
included by two roots, and the error suggested the forecast view.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea

MAIN = """option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Equity:Opening USD
2024-01-02 * "Opening"
  Assets:Cash 1000.00 USD
  Equity:Opening -1000.00 USD
include "entries.bean"
"""
ENTRIES = """2024-01-03 * "Old milk"
  Assets:Cash -3.25 USD
  Expenses:Food 3.25 USD
"""
FORECAST = """option "operating_currency" "USD"
include "main.bean"
{entry}"""
OVERLAY_ENTRY = """2024-03-01 * "Forecast only"
  Assets:Cash -7.00 USD
  Expenses:Food 7.00 USD
"""
CSV = "Date,Description,Amount,Reference\n2024-02-01,Coffee,-4.50,coffee-1\n"
MAPPING = "date=Date,narration=Description,amount=Amount,id=Reference"


def _books(tmp_path: Path, forecast: str) -> None:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "entries.bean").write_text(ENTRIES)
    (tmp_path / "forecast.bean").write_text(forecast)
    (tmp_path / "bank.csv").write_text(CSV)


def _import(tmp_path: Path, *flags: str) -> object:
    return _bea(
        tmp_path,
        "import",
        "bank.csv",
        "--csv",
        MAPPING,
        "--account",
        "Assets:Cash",
        "--default-account",
        "Expenses:Food",
        *flags,
        ledger="entries.bean",
    )


@pytest.mark.parametrize(
    "forecast",
    [
        FORECAST.format(entry=OVERLAY_ENTRY),
        FORECAST.format(entry='2024-03-01 * "Forecast only"\n  Assets:Cash -7.00 USD\n  Expenses:Food 7.00 USD\n'),
        FORECAST.format(entry="; mentions entries.bean in a comment\n"),
    ],
    ids=["overlay", "starred-overlay", "comment"],
)
def test_a_leaf_import_and_note_go_through_the_working_root(tmp_path: Path, forecast: str) -> None:
    _books(tmp_path, forecast)

    preview = _import(tmp_path)
    applied = _import(tmp_path, "--apply")
    again = _import(tmp_path, "--apply")
    noted = _bea(
        tmp_path,
        "add",
        "note",
        "--date",
        "2024-02-02",
        "--account",
        "Assets:Cash",
        "--comment",
        "Reviewed",
        ledger="entries.bean",
    )

    assert preview.returncode == 0, preview.stderr  # type: ignore[attr-defined]
    assert applied.returncode == 0, applied.stderr  # type: ignore[attr-defined]
    assert again.returncode == 0, again.stderr  # type: ignore[attr-defined]
    assert noted.returncode == 0, noted.stderr  # type: ignore[attr-defined]
    written = (tmp_path / "entries.bean").read_text()
    assert written.count("Coffee") == 1
    assert "Reviewed" in written
    assert (tmp_path / "main.bean").read_text() == MAIN
    assert (tmp_path / "forecast.bean").read_text() == forecast
    query = _bea(tmp_path, "query", "SELECT sum(number) WHERE account = 'Assets:Cash'", ledger="main.bean")
    assert json.loads(query.stdout)["data"]["rows"] == [["992.25"]]


def test_two_independent_roots_still_refuse(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "entries.bean").write_text(ENTRIES)
    (tmp_path / "other.bean").write_text(MAIN)
    (tmp_path / "bank.csv").write_text(CSV)

    refused = _import(tmp_path, "--apply")

    assert refused.returncode == 2, refused.stdout  # type: ignore[attr-defined]
    assert "included by more than one root ledger" in refused.stderr  # type: ignore[attr-defined]
    assert (tmp_path / "entries.bean").read_text() == ENTRIES
