"""BQL `filename` names the ledger file on a ledger with a managed price include (w5/099).

The managed loader parses staged copies and mapped entry locations back to
the originals — but not each posting's own location, which is what the
postings table reads. `SELECT filename` named a `.bea-*.tmp` file that changed
every run, and a filter on the source file silently matched nothing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.test_price import _run_bea
from tests.test_price import feed_server as feed_server

ROOT = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
{managed}include "sub/jan.bean"

2026-01-02 * "Lunch"
  Expenses:Food  12.00 USD
  Assets:Cash
"""
CHILD = '2026-01-03 * "Coffee"\n  Expenses:Food  4.50 USD\n  Assets:Cash\n'
FOOD = "SELECT filename, lineno, account WHERE account ~ 'Food' ORDER BY date"


def _books(tmp_path: Path, feed_server: str, *, managed: bool) -> Path:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "jan.bean").write_text(CHILD)
    ledger = tmp_path / "main.bean"
    ledger.write_text(ROOT.format(managed=f'include "{feed_server}/prices/BTC-USD"\n' if managed else ""))
    return ledger


def _query(tmp_path: Path, feed_server: str, ledger: Path, query: str, *flags: str) -> Any:
    result = _run_bea(tmp_path, feed_server, "--file", str(ledger), *flags, "query", query)
    assert result.returncode == 0, result.stderr
    assert ".bea-" not in result.stdout
    return result.stdout


@pytest.mark.parametrize("managed", [True, False], ids=["managed-include", "include-free"])
def test_posting_filenames_name_the_root_and_the_included_child(
    feed_server: str, tmp_path: Path, managed: bool
) -> None:
    ledger = _books(tmp_path, feed_server, managed=managed)

    rows = json.loads(_query(tmp_path, feed_server, ledger, FOOD, "--json"))["data"]["rows"]

    assert [row[0] for row in rows] == [str(ledger), str(tmp_path / "sub" / "jan.bean")]
    lines = ledger.read_text().split("\n")
    assert lines[int(rows[0][1]) - 1] == "  Expenses:Food  12.00 USD"
    assert int(rows[1][1]) == 2


def test_a_filter_on_the_source_file_finds_its_postings(feed_server: str, tmp_path: Path) -> None:
    ledger = _books(tmp_path, feed_server, managed=True)

    total = _query(
        tmp_path, feed_server, ledger, "SELECT sum(position) AS total WHERE filename ~ 'jan' AND account ~ 'Food'"
    )
    by_meta = _query(
        tmp_path, feed_server, ledger, "SELECT account WHERE meta('filename') ~ 'jan.bean' AND account ~ 'Food'"
    )

    assert "4.50 USD" in total
    assert "Expenses:Food" in by_meta


@pytest.mark.parametrize("fmt", ["text", "csv"])
def test_no_output_format_shows_a_staging_name(feed_server: str, tmp_path: Path, fmt: str) -> None:
    ledger = _books(tmp_path, feed_server, managed=True)
    result = _run_bea(tmp_path, feed_server, "--file", str(ledger), "query", FOOD, "-f", fmt)

    assert result.returncode == 0, result.stderr
    assert ".bea-" not in result.stdout
    assert str(tmp_path / "sub" / "jan.bean") in result.stdout
    assert not list(tmp_path.rglob(".bea-*.tmp"))
