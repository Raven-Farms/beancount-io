"""A managed price include beside a multi-file glob keeps the file's line numbers (w5/092).

The staged shadow the managed loader parses wrote a glob's N matches as N
include lines, so every later line was numbered N-1 too high. Authored entries
were then judged `generated`, `--on-disk` hid them, and `add price` no longer
saw its own duplicates.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.test_price import _run_bea
from tests.test_price import feed_server as feed_server

TAIL = """
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening

2026-01-02 * "Opening balance"
  Assets:Checking  1000.00 USD
  Equity:Opening  -1000.00 USD

2026-01-03 price BTC 51000 USD
"""


def _books(tmp_path: Path, feed_server: str, matches: int, extra: str = "") -> Path:
    (tmp_path / "sub").mkdir()
    for name in "abc"[:matches]:
        (tmp_path / "sub" / f"{name}.bean").write_text(f"2026-01-01 open Expenses:{name.upper()}x\n")
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        f'option "operating_currency" "USD"\ninclude "{feed_server}/prices/BTC-USD"\ninclude "sub/*.bean"\n'
        + TAIL
        + extra
    )
    return ledger


def _json(tmp_path: Path, feed_server: str, ledger: Path, *args: str) -> Any:
    result = _run_bea(tmp_path, feed_server, "--json", "--file", str(ledger), *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["data"]


@pytest.mark.parametrize("matches", [1, 2, 3])
def test_authored_entries_are_on_disk_at_their_own_lines(feed_server: str, tmp_path: Path, matches: int) -> None:
    ledger = _books(tmp_path, feed_server, matches)
    lines = ledger.read_text().split("\n")

    (transaction,) = _json(tmp_path, feed_server, ledger, "list", "transaction", "--on-disk")
    prices = _json(tmp_path, feed_server, ledger, "list", "price", "--on-disk")
    listed = _json(tmp_path, feed_server, ledger, "list", "transaction")

    assert transaction["narration"] == "Opening balance"
    assert [price["date"] for price in prices] == ["2026-01-03"]
    assert "generated" not in listed[0]
    query = "SELECT entry_meta('lineno') AS line WHERE narration = 'Opening balance' LIMIT 1"
    rows = _json(tmp_path, feed_server, ledger, "query", query)["rows"]
    assert lines[int(rows[0][0]) - 1] == '2026-01-02 * "Opening balance"'


@pytest.mark.parametrize("matches", [2, 3])
def test_add_price_still_sees_the_price_it_would_duplicate(feed_server: str, tmp_path: Path, matches: int) -> None:
    ledger = _books(tmp_path, feed_server, matches)
    before = ledger.read_text()

    same = _run_bea(
        tmp_path,
        feed_server,
        "--file",
        str(ledger),
        "add",
        "price",
        "--date",
        "2026-01-03",
        "-c",
        "BTC",
        "--amount",
        "51000 USD",
    )
    other = _run_bea(
        tmp_path,
        feed_server,
        "--file",
        str(ledger),
        "add",
        "price",
        "--date",
        "2026-01-03",
        "-c",
        "BTC",
        "--amount",
        "52000 USD",
    )

    assert same.returncode == 0, same.stderr
    assert other.returncode != 0, other.stdout
    assert ledger.read_text() == before


def test_a_failing_assertion_is_reported_at_its_real_line(feed_server: str, tmp_path: Path) -> None:
    ledger = _books(tmp_path, feed_server, 3, extra="2026-01-05 balance Assets:Checking  999.00 USD\n")
    line = ledger.read_text().split("\n").index("2026-01-05 balance Assets:Checking  999.00 USD") + 1

    result = _run_bea(tmp_path, feed_server, "--json", "--file", str(ledger), "check")

    assert result.returncode == 1, result.stdout
    assert f"{ledger}:{line}: Balance failed" in " ".join(json.loads(result.stderr)["error"]["details"])
    assert not list(tmp_path.rglob(".bea-*.tmp"))
