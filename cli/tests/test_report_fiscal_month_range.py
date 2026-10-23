"""A `fiscal-year-end` month outside 01–24 refuses fiscal periods (w5/809).

The vendored parser takes any month modulo 12, so `"00-31"` made `FY2026`
calendar 2025 and `"99-31"` reported 2033-04-01 through 2034-03-31, exit 0.
Months 13 to 24 are Fava's year end in the following calendar year and keep
working.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = """\
option "operating_currency" "USD"
2020-01-01 custom "fava-option" "fiscal-year-end" "{value}"
2024-01-01 open Assets:Checking USD
2024-01-01 open Expenses:Food USD

2026-05-01 * "lunch"
  Expenses:Food  31.00 USD
  Assets:Checking
"""


def _income(tmp_path: Path, value: str, time: str = "FY2026") -> tuple[int, Any]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(value=value))
    result = runner.invoke(app, ["--json", "--file", str(ledger), "report", "income-statement", "--time", time])
    return result.exit_code, json.loads(result.stdout if result.exit_code == 0 else result.stderr)


@pytest.mark.parametrize(("value", "month"), [("00-31", 0), ("25-31", 25), ("99-31", 99)])
def test_a_month_outside_the_range_refuses_the_fiscal_period(tmp_path: Path, value: str, month: int) -> None:
    exit_code, payload = _income(tmp_path, value)

    assert exit_code == 1, payload
    assert "data" not in payload
    assert "fiscal-year-end option is invalid" in payload["error"]["message"]
    assert payload["error"]["details"][0].startswith(f'"{value}" names month {month}; a fiscal year end is MM-DD')


def test_a_calendar_period_ignores_the_month(tmp_path: Path) -> None:
    exit_code, payload = _income(tmp_path, "00-31", "2026")

    assert exit_code == 0, payload
    assert payload["data"]["period"] == {"start": "2026-01-01", "end_exclusive": "2027-01-01"}


@pytest.mark.parametrize(
    ("value", "start", "end"),
    [
        ("15-31", "2026-04-01", "2027-04-01"),
        ("03-31", "2025-04-01", "2026-04-01"),
        ("24-31", "2027-01-01", "2028-01-01"),
    ],
)
def test_months_up_to_24_keep_fava_meaning(tmp_path: Path, value: str, start: str, end: str) -> None:
    exit_code, payload = _income(tmp_path, value)

    assert exit_code == 0, payload
    assert payload["data"]["period"] == {"start": start, "end_exclusive": end}
