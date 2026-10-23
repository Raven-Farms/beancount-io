"""Fiscal periods that start in year zero are answered when the requested bounds are representable (w5/932).

`FY0001` and `FY0001-Q1` built the previous year's end (year 0) as an
intermediate and refused with "year 0 is out of range", while `0001` and
`0001-Q1` reported the same periods. A June year end's Q3 of FY0001 is
0001-01-01 to 0001-04-01 although the whole fiscal year starts in year 0.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from fava.util.date import get_fiscal_period, parse_fye_string
from tests.test_import_source_facts import _bea

LEDGER = """option "operating_currency" "USD"
{option}0001-01-01 open Assets:Cash USD
0001-01-01 open Income:Salary USD
0001-01-02 * "First salary"
  Assets:Cash 10.00 USD
  Income:Salary -10.00 USD
0002-01-02 * "Second salary"
  Assets:Cash 20.00 USD
  Income:Salary -20.00 USD
"""


def _report(tmp_path: Path, time: str, fye: str | None = None) -> tuple[int, dict[str, object]]:
    option = f'0001-01-01 custom "fava-option" "fiscal-year-end" "{fye}"\n' if fye else ""
    (tmp_path / "main.bean").write_text(LEDGER.format(option=option))
    result = _bea(tmp_path, "report", "income-statement", "--time", time, "--interval", "quarterly")
    return result.returncode, json.loads(result.stdout or result.stderr)


@pytest.mark.parametrize("fye", [None, "12-31"])
@pytest.mark.parametrize(("fiscal", "calendar"), [("FY0001", "0001"), ("FY0001-Q1", "0001-Q1")])
def test_year_one_fiscal_periods_match_their_calendar_spelling(
    tmp_path: Path, fye: str | None, fiscal: str, calendar: str
) -> None:
    code, expected = _report(tmp_path, calendar, fye)
    assert code == 0, expected

    code, payload = _report(tmp_path, fiscal, fye)

    assert code == 0, payload
    assert payload["data"] == expected["data"]


def test_a_june_year_end_third_quarter_is_the_first_calendar_quarter(tmp_path: Path) -> None:
    code, expected = _report(tmp_path, "0001-Q1")
    assert code == 0, expected

    code, payload = _report(tmp_path, "FY0001-Q3", "06-30")

    assert code == 0, payload
    assert payload["data"] == expected["data"]


def test_the_whole_fiscal_year_that_starts_in_year_zero_is_still_refused(tmp_path: Path) -> None:
    code, payload = _report(tmp_path, "FY0001", "06-30")

    assert code == 2, payload
    assert "year 0 is out of range" in json.dumps(payload)


def test_fiscal_year_zero_is_still_refused(tmp_path: Path) -> None:
    code, payload = _report(tmp_path, "FY0000")

    assert code == 2, payload


@pytest.mark.parametrize(
    ("year", "fye", "quarter", "expected"),
    [
        (1, "12-31", None, (datetime.date(1, 1, 1), datetime.date(2, 1, 1))),
        (2026, "06-30", 3, (datetime.date(2026, 1, 1), datetime.date(2026, 4, 1))),
        (2026, "03-31", None, (datetime.date(2025, 4, 1), datetime.date(2026, 4, 1))),
        (2025, "02-28", None, (datetime.date(2024, 3, 1), datetime.date(2025, 3, 1))),
        (2026, "15-31", 1, (datetime.date(2026, 4, 1), datetime.date(2026, 7, 1))),
        (2026, "01-15", None, (datetime.date(2025, 1, 16), datetime.date(2026, 1, 16))),
    ],
)
def test_ordinary_fiscal_bounds_are_unchanged(
    year: int, fye: str, quarter: int | None, expected: tuple[datetime.date, datetime.date]
) -> None:
    assert get_fiscal_period(year, parse_fye_string(fye), quarter) == expected
