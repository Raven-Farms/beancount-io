"""`list --on-disk` leaves out a managed feed's prices, and plain `list` marks them (w5/070).

A feed entry's line is real, but it sits in the price cache rather than in
any file of the ledger, so the line-matching test for "written" passed it.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_price import _run_bea, _write_managed_ledger
from tests.test_price import feed_server as feed_server

AUTHORED = "\n2026-09-09 price BTC  111000 USD\n"


def _prices(tmp_path: Path, feed_server: str, ledger: Path, *flags: str) -> list[dict[str, object]]:
    result = _run_bea(tmp_path, feed_server, "--json", "--file", str(ledger), "list", "price", *flags)
    assert result.returncode == 0, result.stderr
    items: list[dict[str, object]] = json.loads(result.stdout)["data"]
    return items


def test_on_disk_returns_only_the_price_the_ledger_file_declares(feed_server: str, tmp_path: Path) -> None:
    ledger = _write_managed_ledger(tmp_path, feed_server, AUTHORED)

    rows = _prices(tmp_path, feed_server, ledger, "--on-disk")
    human = _run_bea(tmp_path, feed_server, "--file", str(ledger), "list", "price", "--on-disk")

    assert [row["date"] for row in rows] == ["2026-09-09"]
    assert "generated" not in rows[0]
    assert human.returncode == 0, human.stderr
    assert "111000" in human.stdout
    assert "112000.00" not in human.stdout and "113500.50" not in human.stdout
    assert ledger.read_text().count("price BTC") == 1


def test_an_unfiltered_listing_marks_the_feed_rows(feed_server: str, tmp_path: Path) -> None:
    ledger = _write_managed_ledger(tmp_path, feed_server, AUTHORED)

    rows = _prices(tmp_path, feed_server, ledger)
    human = _run_bea(tmp_path, feed_server, "--file", str(ledger), "list", "price")

    assert {row["date"]: row.get("generated", False) for row in rows} == {
        "2026-09-09": False,
        "2026-09-10": True,
        "2026-09-11": True,
    }
    assert "SOURCE" in human.stdout
    assert human.stdout.count("generated") == 2


def test_an_exported_snapshot_lists_the_feed_prices_as_written(feed_server: str, tmp_path: Path) -> None:
    ledger = _write_managed_ledger(tmp_path, feed_server, AUTHORED)
    assert _run_bea(tmp_path, feed_server, "--file", str(ledger), "price", "export").returncode == 0
    exported = tmp_path / "main-export" / "main.bean"

    rows = _prices(tmp_path, feed_server, exported, "--on-disk")

    assert [row["date"] for row in rows] == ["2026-09-09", "2026-09-10", "2026-09-11"]
    assert not any("generated" in row for row in rows)
