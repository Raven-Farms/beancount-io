"""`-t "year - year+1"` parses like `(year) - (year+1)` (w5/618).

The vendored Fava date parser replaced every occurrence of a matched
variable, so the bare `year` in `year - year+1` also rewrote the start of
`year+1` into `2026+1`, and the range was refused with exit 2. Compared
against the parenthesized spelling, so the test does not depend on today.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from fava.util.date import parse_date

runner = CliRunner()
SPELLINGS = ["year - year+1", "month - month+2", "day - day+7", "quarter - quarter+1", "week - week+1"]


def _parenthesized(spelling: str) -> str:
    start, end = spelling.split(" - ")
    return f"({start}) - ({end})"


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_a_bare_variable_range_parses_like_the_parenthesized_one(spelling: str) -> None:
    begin, end = parse_date(spelling)

    assert begin is not None and end is not None and begin < end
    assert (begin, end) == parse_date(_parenthesized(spelling))


def test_the_report_accepts_the_bare_spelling(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text('option "operating_currency" "USD"\n2026-01-01 open Income:Salary USD\n')

    bare = runner.invoke(app, ["--json", "-f", str(ledger), "report", "income-statement", "-t", "year - year+1"])
    grouped = runner.invoke(app, ["--json", "-f", str(ledger), "report", "income-statement", "-t", "(year) - (year+1)"])

    assert bare.exit_code == 0, bare.output
    assert json.loads(bare.stdout)["data"]["period"] == json.loads(grouped.stdout)["data"]["period"]
