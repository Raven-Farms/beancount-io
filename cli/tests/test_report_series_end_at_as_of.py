"""Without `--time`, interval series end on the report's as-of date (w5/261).

The last range ran out to the next interval boundary, so a ledger whose last
entry is 2026-02-10 dated its yearly net-worth point 2026-12-31 — after the
`as_of` the same report published, and on a different day for every interval.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD
2026-01-01 open Expenses:Food USD
2026-01-02 * "Opening"
  Assets:Cash        1000.00 USD
  Equity:Opening    -1000.00 USD
2026-02-10 * "Lunch"
  Expenses:Food        10.00 USD
  Assets:Cash         -10.00 USD
"""
AS_OF = "2026-02-10"
INTERVALS = ("daily", "weekly", "monthly", "quarterly", "yearly")


def _bea(tmp_path: Path, *args: str) -> str:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout


def _report(tmp_path: Path, *args: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(_bea(tmp_path, "--json", "-f", "main.bean", "report", *args))["data"]
    return data


def _series(kind: str, data: dict[str, Any]) -> dict[str, list[str]]:
    """Every interval series a report carries, as its list of dates."""
    if kind == "balance-sheet":
        series = {"net_worth_series": data["net_worth_series"]}
    elif kind == "income-statement":
        series = {"periods": data["periods"]}
    else:
        series = data["series"]
    return {name: [point["date"] for point in points] for name, points in series.items()}


@pytest.mark.parametrize("interval", INTERVALS)
@pytest.mark.parametrize("kind", ["overview", "income-statement", "balance-sheet"])
def test_no_series_date_exceeds_as_of(tmp_path: Path, kind: str, interval: str) -> None:
    data = _report(tmp_path, kind, "-i", interval)

    assert data["as_of"] == AS_OF
    for name, dates in _series(kind, data).items():
        assert dates[-1] == AS_OF, name
        assert dates == sorted(set(dates)), name


def test_yearly_balance_sheet_matches_the_time_filtered_control(tmp_path: Path) -> None:
    point = [{"date": AS_OF, "balance": {"USD": "990.00"}}]

    bare = _report(tmp_path, "balance-sheet", "-i", "yearly")
    control = _report(tmp_path, "balance-sheet", "-i", "yearly", "-t", "2026-01-02 - 2026-02-10")

    assert control["as_of"] == AS_OF
    assert control["net_worth_series"] == point
    assert bare["net_worth_series"] == point
    assert bare["period"] == control["period"]


def test_earlier_buckets_stay_whole(tmp_path: Path) -> None:
    data = _report(tmp_path, "balance-sheet", "-i", "monthly")

    assert data["net_worth_series"] == [
        {"date": "2026-01-31", "balance": {"USD": "1000.00"}},
        {"date": AS_OF, "balance": {"USD": "990.00"}},
    ]


def test_text_income_statement_dates_its_row_at_as_of(tmp_path: Path) -> None:
    out = _bea(tmp_path, "-f", "main.bean", "report", "income-statement", "-i", "quarterly")

    assert "Income Statement — 2026-01-02 through 2026-02-10" in out
    rows = [line.split()[0] for line in out.splitlines() if line.startswith("20")]
    assert rows == [AS_OF]
