"""Query-text mistakes that only fail while rows are evaluated are usage errors (w5/314).

`parse_date('x')`, date arithmetic past the calendar and a `LIMIT` beyond
`sys.maxsize` exited 1 as `validation` behind `ParserError:`, `OverflowError:`
or `ValueError:`, and `query --source` printed a boxed traceback for them.
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
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Equity:Opening
2026-01-05 * "Lunch"
  Expenses:Food  12.50 USD
  Assets:Checking
"""
CLASS_NAMES = ("ParserError", "OverflowError", "ValueError", "Traceback")


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


CASES = [
    ("SELECT parse_date('x')", "cannot read a date: Unknown string format: x"),
    ("SELECT date WHERE date > parse_date('nope')", "Unknown string format: nope"),
    ("SELECT parse_date('2026-13-45')", "2026-13-45"),
    ("SELECT date + 99999999", "date value out of range"),
    ("SELECT date_add(date, 9999999)", "date value out of range"),
    ("SELECT account LIMIT 9223372036854775808", f"LIMIT must be at most {sys.maxsize}"),
]


@pytest.mark.parametrize(("statement", "named"), CASES)
def test_a_query_text_mistake_is_a_usage_error(tmp_path: Path, statement: str, named: str) -> None:
    result = _bea(tmp_path, "-f", str(tmp_path / "main.bean"), "query", statement)
    assert result.returncode == 2, result.stderr
    assert "Cannot run this BQL query:" in result.stderr
    assert named in result.stderr
    assert not any(name in result.stderr for name in CLASS_NAMES), result.stderr


@pytest.mark.parametrize(("statement", "named"), CASES[:1] + CASES[3:4] + CASES[5:])
def test_json_reports_category_usage(tmp_path: Path, statement: str, named: str) -> None:
    result = _bea(tmp_path, "--json", "-f", str(tmp_path / "main.bean"), "query", statement)
    assert result.returncode == 2
    error = json.loads(result.stdout or result.stderr)["error"]
    assert error["category"] == "usage"
    assert error["message"].startswith("Cannot run this BQL query:")
    assert named in error["message"]


@pytest.mark.parametrize("statement", [CASES[0][0], CASES[3][0], CASES[5][0]])
def test_native_source_names_the_mistake_in_one_line(tmp_path: Path, statement: str) -> None:
    result = _bea(tmp_path, "query", "--source", str(tmp_path / "main.bean"), statement)
    assert result.returncode == 2, result.stderr
    assert result.stderr.splitlines()[0].startswith("error: Cannot run this BQL query:")
    assert not any(name in result.stderr for name in CLASS_NAMES), result.stderr


def test_the_largest_allowed_limit_still_answers(tmp_path: Path) -> None:
    result = _bea(tmp_path, "-f", str(tmp_path / "main.bean"), "query", f"SELECT account LIMIT {sys.maxsize}")
    assert result.returncode == 0, result.stderr
    assert "Expenses:Food" in result.stdout
