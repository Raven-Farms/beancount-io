"""A filter that starts partway through an interval drops its empty leading fragment (w5/365).

w3/375 dropped a quiet *trailing* fragment from flow series; the first range
is clipped the same way, and `-t 2026-03 -i weekly` opened with a one-day
Sunday "week" of zeros. Fragments holding entries, a filter's only range and
balance series keep every bucket.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2025-01-01 open Assets:Cash USD
2025-01-01 open Expenses:Food USD
2025-01-01 open Income:Salary USD
2026-02-27 * "feb"
  Expenses:Food 5 USD
  Assets:Cash
2026-03-05 * "groceries"
  Expenses:Food 40 USD
  Assets:Cash
2026-03-20 * "pay"
  Assets:Cash 1000 USD
  Income:Salary
"""


def _data(tmp_path: Path, *args: str) -> dict:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", "main.bean", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["data"]


def _periods(tmp_path: Path, time: str, interval: str) -> list[tuple[str, str]]:
    data = _data(tmp_path, "report", "income-statement", "-t", time, "-i", interval)
    return [(period["date"], period["expenses"]["USD"]) for period in data["periods"]]


@pytest.mark.parametrize(
    ("time", "interval", "expected"),
    [
        # 2026-03-01 is a Sunday: the last day of an ISO week, and empty.
        ("2026-03", "weekly", [("2026-03-08", "40"), ("2026-03-15", "0"), ("2026-03-22", "0"), ("2026-03-29", "0")]),
        ("2026-01-31 - 2026-03-31", "monthly", [("2026-02-28", "5"), ("2026-03-31", "40")]),
        ("2025-12-31 - 2026-12-31", "yearly", [("2026-12-31", "45")]),
        ("2025-09-30 - 2026-03-31", "quarterly", [("2025-12-31", "0"), ("2026-03-31", "45")]),
    ],
    ids=["weekly", "monthly", "yearly", "quarterly"],
)
def test_a_quiet_leading_fragment_is_not_a_period(
    tmp_path: Path, time: str, interval: str, expected: list[tuple[str, str]]
) -> None:
    assert _periods(tmp_path, time, interval) == expected


def test_a_leading_fragment_with_entries_stays(tmp_path: Path) -> None:
    # Friday 2026-02-27 to Sunday 2026-03-01 holds the 5 USD lunch.
    assert _periods(tmp_path, "2026-02-27 - 2026-03-31", "weekly")[0] == ("2026-03-01", "5")


def test_a_filter_of_two_quiet_fragments_keeps_one(tmp_path: Path) -> None:
    assert _periods(tmp_path, "2026-03-01 - 2026-03-02", "weekly") == [("2026-03-01", "0")]


def test_balance_series_keep_the_leading_bucket(tmp_path: Path) -> None:
    data = _data(tmp_path, "report", "balance-sheet", "-t", "2026-03", "-i", "weekly")
    dates = [point["date"] for point in data["net_worth_series"]]
    assert dates[0] == "2026-03-01"
    assert dates[-1] == "2026-03-31"
