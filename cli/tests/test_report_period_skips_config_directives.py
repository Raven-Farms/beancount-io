"""A placeholder-dated `custom` or `query` does not set the report period (w5/193).

Configuration directives are conventionally dated long before any activity
(`1970-01-01 custom "fava-option" …`). The period bounds already skipped
Open, Close and Commodity for that reason; a `custom` or a stored `query` was
taken as the first day of the ledger, so the heading read "1970-01-01 through
2024-05-17" and the monthly series carried 652 empty months.

Notes, balances and events stay dated facts (w3/349).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

BODY = """2024-01-01 open Assets:Bank
2024-01-01 open Income:Job
2024-05-17 * "pay"
  Assets:Bank  10.00 USD
  Income:Job
"""
HEAD = 'option "operating_currency" "USD"\n'

DECLARATIONS = {
    "custom": '1970-01-01 custom "fava-option" "language" "en"\n',
    "query": '1970-01-01 query "all" "SELECT account, sum(position) GROUP BY account"\n',
    "commodity": "1970-01-01 commodity USD\n",
}
KINDS = ["overview", "income-statement", "balance-sheet", "trial-balance"]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _ledger(tmp_path: Path, text: str) -> str:
    path = tmp_path / "main.bean"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _data(tmp_path: Path, ledger: str, *args: str) -> dict:
    done = _bea(tmp_path, "--json", "--file", ledger, *args)
    assert done.returncode == 0, done.stderr or done.stdout
    return json.loads(done.stdout)["data"]


@pytest.mark.parametrize("directive", sorted(DECLARATIONS))
@pytest.mark.parametrize("kind", KINDS)
def test_an_early_declaration_does_not_start_the_period(tmp_path: Path, directive: str, kind: str) -> None:
    """`commodity` is the control: it was already exempt."""
    data = _data(tmp_path, _ledger(tmp_path, HEAD + DECLARATIONS[directive] + BODY), "report", kind)

    assert data["period"] == {"start": "2024-05-17", "end_exclusive": "2024-05-18"}
    assert data["as_of"] == "2024-05-17"


@pytest.mark.parametrize("directive", ["custom", "query"])
def test_the_interval_series_has_one_row(tmp_path: Path, directive: str) -> None:
    ledger = _ledger(tmp_path, HEAD + DECLARATIONS[directive] + BODY)

    monthly = _data(tmp_path, ledger, "report", "income-statement")
    assert len(monthly["periods"]) == 1, [period["date"] for period in monthly["periods"]][:5]

    daily = _data(tmp_path, ledger, "report", "income-statement", "-i", "daily")
    assert [period["date"] for period in daily["periods"]] == ["2024-05-17"]


@pytest.mark.parametrize("directive", ["custom", "query"])
def test_the_headings_name_the_active_period(tmp_path: Path, directive: str) -> None:
    ledger = _ledger(tmp_path, HEAD + DECLARATIONS[directive] + BODY)

    for args in (("report", "balance-sheet"), ("report", "overview"), ("balance",)):
        done = _bea(tmp_path, "--file", ledger, *args)
        assert done.returncode == 0, done.stderr or done.stdout
        assert "2024-05-17 through 2024-05-17" in done.stdout, f"{args}: {done.stdout[:200]}"
        assert "1970" not in done.stdout, args
        assert len(done.stdout.splitlines()) < 40, f"{args}: zero rows flood the series"


@pytest.mark.parametrize("directive", ["custom", "query"])
def test_a_late_declaration_does_not_end_the_period(tmp_path: Path, directive: str) -> None:
    late = DECLARATIONS[directive].replace("1970-01-01", "2099-01-01")
    data = _data(tmp_path, _ledger(tmp_path, HEAD + BODY + late), "report", "balance-sheet")

    assert data["as_of"] == "2024-05-17"


@pytest.mark.parametrize(
    "fact",
    [
        '2023-11-02 note Assets:Bank "opened by post"\n',
        '2023-11-02 event "location" "Berlin"\n',
    ],
)
def test_an_early_dated_fact_still_starts_the_period(tmp_path: Path, fact: str) -> None:
    """Notes and events date something that happened; w3/349 keeps them in."""
    opens = "2023-01-01 open Assets:Bank\n2023-01-01 open Income:Job\n"
    body = BODY.replace("2024-01-01 open Assets:Bank\n2024-01-01 open Income:Job\n", opens + fact)
    data = _data(tmp_path, _ledger(tmp_path, HEAD + body), "report", "income-statement")

    assert data["period"]["start"] == "2023-11-02"
    assert data["as_of"] == "2024-05-17"
    assert len(data["periods"]) == 7


def test_a_late_note_still_ends_the_period(tmp_path: Path) -> None:
    text = HEAD + DECLARATIONS["custom"] + BODY + '2024-08-03 note Assets:Bank "statement filed"\n'
    data = _data(tmp_path, _ledger(tmp_path, text), "report", "income-statement")

    assert data["period"]["start"] == "2024-05-17"
    assert data["as_of"] == "2024-08-03"


def test_the_boundary_check_skips_the_same_declarations() -> None:
    """A `custom` on 9999-12-31 is not the dated fact a report cannot bound."""
    from datetime import date

    from beancount.core.data import Custom, Note, Query

    from bea_engine.report import _unreportable_boundary

    meta: dict = {}
    declarations = [
        Custom(meta, date.max, "fava-option", []),
        Query(meta, date.max, "all", "SELECT account"),
    ]
    assert _unreportable_boundary(declarations) is None

    assert _unreportable_boundary([*declarations, Note(meta, date.max, "Assets:Bank", "x", None, None)]) == date.max
