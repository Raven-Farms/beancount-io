"""A period that stops short of 9999-12-31 says so (w5/194).

A report's period is exclusive at the end and `datetime.date` has no day after
9999-12-31, so `--time 9999` clamps its end to that day and covers the year
through 9999-12-30. The unfiltered report on such a ledger refuses and names
`--time 9999` as the way to get an answer; following it used to exit 0 with
the 9999-12-31 entries missing and nothing saying so. The report still cannot
include that day — it now states the exclusion, in text and in JSON, and the
refusal no longer promises a complete report.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

BOUNDARY = """option "operating_currency" "USD"
9999-12-31 open Assets:Cash USD
9999-12-31 open Equity:Opening USD
9999-12-31 * "Boundary"
  Assets:Cash 1 USD
  Equity:Opening
"""
DAY_BEFORE = BOUNDARY.replace("9999-12-31", "9999-12-30")
MIXED = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD
2026-05-01 * "May"
  Assets:Cash 10 USD
  Equity:Opening
9999-12-31 * "Boundary"
  Assets:Cash 5 USD
  Equity:Opening
"""
NOTICE = "Entries dated 9999-12-31 are not included"

KINDS = ["overview", "income-statement", "balance-sheet", "trial-balance"]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _ledger(tmp_path: Path, text: str) -> str:
    path = tmp_path / "main.bean"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _data(done: subprocess.CompletedProcess[str]) -> dict:
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)["data"]


def test_the_recommended_period_states_what_it_leaves_out(tmp_path: Path) -> None:
    """The note's command: exit 0 is kept, the silence is not."""
    done = _bea(tmp_path, "-f", _ledger(tmp_path, BOUNDARY), "balance", "-t", "9999")

    assert done.returncode == 0, done.stderr
    assert "9999-01-01 through 9999-12-30" in done.stdout
    assert "1 USD" not in done.stdout, "the entry is still out of reach"
    assert NOTICE in done.stderr, done.stderr


def test_json_carries_the_excluded_date(tmp_path: Path) -> None:
    data = _data(_bea(tmp_path, "--json", "-f", _ledger(tmp_path, BOUNDARY), "balance", "-t", "9999"))

    assert data["excluded_date"] == "9999-12-31"
    assert data["as_of"] == "9999-12-30"
    assert data["assets"]["balance_children"] == {}


@pytest.mark.parametrize("kind", KINDS)
def test_every_report_kind_states_it(tmp_path: Path, kind: str) -> None:
    done = _bea(tmp_path, "-f", _ledger(tmp_path, BOUNDARY), "report", kind, "-t", "9999")

    assert done.returncode == 0, done.stderr
    assert NOTICE in done.stderr, done.stderr


@pytest.mark.parametrize("time", ["9999-12", "9999-Q4", "2026 - 9999"])
def test_every_period_clamped_at_the_last_day_states_it(tmp_path: Path, time: str) -> None:
    """The clamp is per interval size; a range ending in the year hits it too."""
    done = _bea(tmp_path, "-f", _ledger(tmp_path, MIXED), "balance", "-t", time)

    assert done.returncode == 0, done.stderr
    assert "5 USD" not in done.stdout, "the boundary entry is not in any of these periods"
    assert NOTICE in done.stderr, done.stderr


def test_the_day_before_reports_in_full_and_says_nothing(tmp_path: Path) -> None:
    """Control: the same window on a ledger that fits inside it is unchanged."""
    ledger = _ledger(tmp_path, DAY_BEFORE)
    done = _bea(tmp_path, "-f", ledger, "balance", "-t", "9999")

    assert done.returncode == 0, done.stderr
    assert "9999-01-01 through 9999-12-30" in done.stdout
    assert "-1 USD" in done.stdout
    assert done.stderr == ""

    data = _data(_bea(tmp_path, "--json", "-f", ledger, "balance", "-t", "9999"))
    assert "excluded_date" not in data
    assert data["assets"]["balance_children"] == {"USD": "1"}


def test_a_period_that_ends_earlier_says_nothing(tmp_path: Path) -> None:
    """Leaving 9999-12-31 out of 2026 is what the caller asked for."""
    ledger = _ledger(tmp_path, MIXED)
    done = _bea(tmp_path, "-f", ledger, "balance", "-t", "2026")

    assert done.returncode == 0, done.stderr
    assert "10 USD" in done.stdout
    assert done.stderr == ""
    assert "excluded_date" not in _data(_bea(tmp_path, "--json", "-f", ledger, "balance", "-t", "2026"))


def test_the_refusal_no_longer_promises_a_complete_report(tmp_path: Path) -> None:
    done = _bea(tmp_path, "--json", "-f", _ledger(tmp_path, BOUNDARY), "balance")

    assert done.returncode == 2, done.stdout
    hint = next(detail for detail in json.loads(done.stderr)["error"]["details"] if "--time" in detail)
    assert "--time 9999" in hint, hint
    assert "reports fine" not in hint
    assert "entries dated 9999-12-31 itself are left out" in hint, hint
