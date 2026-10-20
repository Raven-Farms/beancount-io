"""A misspelled `fiscal-year-end` name refuses fiscal periods instead of reporting the calendar year (w5/807).

`custom "fava-option" "fiscal-year-ends" "06-30"` left the calendar-year
default in place, so `-t FY2026` reported January through December, exit 0,
with nothing said; Fava flags the unknown option, but bea dropped that error.
bea reads no other Fava option, so a near miss of this one is refused,
naming its line.
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
2020-01-01 custom "fava-option" "{name}" "06-30"
2024-01-01 open Assets:Checking USD
2024-01-01 open Expenses:Food USD

2025-12-31 * "in FY2026"
  Expenses:Food  31.00 USD
  Assets:Checking
"""


def _income(tmp_path: Path, name: str, time: str = "FY2026") -> tuple[int, Any, Path]:
    ledger = tmp_path / "typo.bean"
    ledger.write_text(LEDGER.format(name=name))
    result = runner.invoke(app, ["--json", "--file", str(ledger), "report", "income-statement", "--time", time])
    return result.exit_code, json.loads(result.stdout if result.exit_code == 0 else result.stderr), ledger


@pytest.mark.parametrize("name", ["fiscal-year-ends", "fiscalyearend", "fiscal year end", "Fiscal-Year-End"])
def test_a_near_miss_refuses_the_fiscal_period_naming_its_line(tmp_path: Path, name: str) -> None:
    exit_code, payload, ledger = _income(tmp_path, name)

    assert exit_code == 1, payload
    assert "fiscal-year-end option looks misspelled" in payload["error"]["message"]
    detail = payload["error"]["details"][0]
    assert detail.startswith(f"{ledger}:2: ")
    assert detail.endswith("It looks like fiscal-year-end, the only Fava option bea reads.")


def test_other_unknown_options_and_calendar_periods_are_unaffected(tmp_path: Path) -> None:
    exit_code, payload, _ = _income(tmp_path, "currency-column")
    assert exit_code == 0, payload
    assert payload["data"]["period"] == {"start": "2026-01-01", "end_exclusive": "2027-01-01"}

    exit_code, payload, _ = _income(tmp_path, "fiscal-year-ends", "2026")
    assert exit_code == 0, payload


def test_the_correct_spelling_still_reports_the_fiscal_year(tmp_path: Path) -> None:
    exit_code, payload, _ = _income(tmp_path, "fiscal-year-end")

    assert exit_code == 0, payload
    assert payload["data"]["period"] == {"start": "2025-07-01", "end_exclusive": "2026-07-01"}
    assert payload["data"]["net_profit"] == {"USD": "-31.00"}
