"""A BQL window of zero days is refused, not answered with (no rows) (w3/372)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD

2024-03-10 * "Lunch"
  Expenses:Food   12.00 USD
  Assets:Cash    -12.00 USD

2024-03-12 * "Dinner"
  Expenses:Food   20.00 USD
  Assets:Cash    -20.00 USD
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        HOME=str(tmp_path / "home"),
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
        timeout=60,
    )


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def test_same_day_window_is_refused_with_the_inclusive_alternatives(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        "--file",
        str(_ledger(tmp_path)),
        "query",
        "SELECT date, narration FROM OPEN ON 2024-03-10 CLOSE ON 2024-03-10",
    )
    assert result.returncode == 2
    assert "covers no days" in result.stderr
    assert "CLOSE ON 2024-03-11" in result.stderr
    assert "--from-date 2024-03-10 --to-date 2024-03-10" in result.stderr
    assert "(no rows)" not in result.stderr


def test_the_refusal_reaches_json_callers(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        "--json",
        "--file",
        str(_ledger(tmp_path)),
        "query",
        "SELECT date FROM OPEN ON 2024-03-10 CLOSE ON 2024-03-10",
    )
    assert result.returncode == 2
    # --json puts the envelope on stdout and errors on stderr.
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert "covers no days" in error["message"]


def test_reversed_window_is_refused(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        "--file",
        str(_ledger(tmp_path)),
        "query",
        "SELECT date FROM OPEN ON 2024-03-12 CLOSE ON 2024-03-10",
    )
    assert result.returncode == 2
    assert "covers no days" in result.stderr


def test_the_suggested_window_returns_that_day(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        "--json",
        "--file",
        str(_ledger(tmp_path)),
        "query",
        'SELECT date, narration FROM OPEN ON 2024-03-10 CLOSE ON 2024-03-11 WHERE narration ~ "Lunch"',
    )
    assert result.returncode == 0, result.stderr
    rows = json.loads(result.stdout)["data"]["rows"]
    assert rows and all(row[0] == "2024-03-10" for row in rows)


def test_queries_without_a_date_window_are_untouched(tmp_path: Path) -> None:
    ledger = str(_ledger(tmp_path))
    for query in ("SELECT count(*)", "SELECT date FROM OPEN ON 2024-03-01", ".tables"):
        result = _bea(tmp_path, "--file", ledger, "query", query)
        assert result.returncode == 0, f"{query}: {result.stderr}"


def test_an_empty_but_real_window_still_answers_no_rows(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        "--file",
        str(_ledger(tmp_path)),
        "query",
        'SELECT date FROM OPEN ON 2024-03-11 CLOSE ON 2024-03-12 WHERE narration ~ "Nothing"',
    )
    assert result.returncode == 0, result.stderr
    assert "(no rows)" in result.stderr


SUBQUERY = "SELECT date, narration FROM (SELECT date, narration FROM OPEN ON {open} CLOSE ON {close})"


@pytest.mark.parametrize(
    "query",
    [
        SUBQUERY,
        SUBQUERY + " WHERE date = {open}",
        "SELECT date WHERE date IN (SELECT date FROM OPEN ON {open} CLOSE ON {close})",
    ],
    ids=["from-subquery", "from-subquery-where", "where-subquery"],
)
def test_a_zero_day_window_inside_a_subquery_is_refused(tmp_path: Path, query: str) -> None:
    """The outer FROM was the only one checked (w1/158)."""
    result = _bea(
        tmp_path, "--file", str(_ledger(tmp_path)), "query", query.format(open="2024-03-10", close="2024-03-10")
    )

    assert result.returncode == 2, result.stdout
    assert "covers no days" in result.stderr
    assert "Use CLOSE ON 2024-03-11 to cover 2024-03-10." in result.stderr


def test_a_reversed_window_inside_a_subquery_gets_the_hint(tmp_path: Path) -> None:
    result = _bea(
        tmp_path, "--file", str(_ledger(tmp_path)), "query", SUBQUERY.format(open="2024-03-12", close="2024-03-10")
    )

    assert result.returncode == 2
    assert "Did you mean OPEN ON 2024-03-10 CLOSE ON 2024-03-13?" in result.stderr


def test_a_valid_subquery_window_still_answers(tmp_path: Path) -> None:
    result = _bea(
        tmp_path, "--file", str(_ledger(tmp_path)), "query", SUBQUERY.format(open="2024-03-10", close="2024-03-11")
    )

    assert result.returncode == 0, result.stderr
    assert "Lunch" in result.stdout


FOOD = "WHERE account = 'Expenses:Food'"
STORED = LEDGER + (
    f'2024-03-11 query "since-11" "SELECT date, narration FROM OPEN ON 2024-03-11 {FOOD}"\n'
    f'2024-03-11 query "since-april" "SELECT date FROM OPEN ON 2024-04-01 {FOOD}"\n'
    f'2024-03-11 query "since-march" "SELECT date, narration FROM OPEN ON 2024-03-01 {FOOD}"\n'
)


@pytest.mark.parametrize(
    ("name", "where", "close"),
    [("since-11", "on that same day", "2024-03-12"), ("since-april", "after it, on 2024-04-01", "2024-04-02")],
    ids=["opens-on-the-directive-date", "opens-after-it"],
)
def test_a_stored_window_closed_by_its_directive_date_is_refused(
    tmp_path: Path, name: str, where: str, close: str
) -> None:
    """Beanquery closes a stored query's window at its directive's date when the text names no close (w5/559)."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(STORED)
    message = (
        "This stored query's window covers no days: its query directive's date, 2024-03-11, closes the window "
        f"(exclusive), and OPEN ON starts {where}."
    )

    text = _bea(tmp_path, "--file", str(ledger), "query", f".run {name}")
    as_json = _bea(tmp_path, "--json", "--file", str(ledger), "query", f".run {name}")

    assert text.returncode == 2, text.stdout + text.stderr
    assert message in " ".join(text.stderr.split()), text.stderr
    assert "CLOSE date must follow OPEN date" not in text.stderr and "(no rows)" not in text.stdout
    error = json.loads(as_json.stderr)["error"]
    assert (error["exit_code"], error["message"]) == (2, message)
    assert error["details"] == [
        f"Add CLOSE ON {close} or later to the query, or re-date its query directive "
        "after the last day it should cover."
    ]


def test_a_stored_window_the_directive_date_leaves_open_still_answers(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(STORED)

    result = _bea(tmp_path, "--file", str(ledger), "query", ".run since-march")

    assert result.returncode == 0, result.stderr
    assert "Lunch" in result.stdout and "Dinner" not in result.stdout
