"""A fiscal period is refused when `fiscal-year-end` did not parse (w5/147).

Option parsing collected the bad value and kept the calendar-year default, so
`--time FY2026` reported January through December, exit 0, with nothing saying
the declared year end had been dropped.
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

2025-12-31 * "in FY2026"
  Expenses:Food  31.00 USD
  Assets:Checking

2026-10-01 * "in FY2027"
  Expenses:Food  10.00 USD
  Assets:Checking
"""
COMMANDS = [
    ["balance"],
    ["report", "overview"],
    ["report", "balance-sheet"],
    ["report", "income-statement"],
    ["report", "trial-balance"],
]
COMMAND_IDS = [" ".join(command) for command in COMMANDS]


def _ledger(tmp_path: Path, value: str) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(value=value))
    return ledger


def _json(ledger: Path, *command: str) -> tuple[int, Any]:
    result = runner.invoke(app, ["--json", "--file", str(ledger), *command])
    return result.exit_code, json.loads(result.stdout if result.exit_code == 0 else result.stderr)


@pytest.mark.parametrize("command", COMMANDS, ids=COMMAND_IDS)
def test_a_fiscal_year_is_refused_naming_the_option(tmp_path: Path, command: list[str]) -> None:
    ledger = _ledger(tmp_path, "06-31")
    assert runner.invoke(app, ["--file", str(ledger), "check"]).exit_code == 0

    exit_code, payload = _json(ledger, *command, "--time", "FY2026")

    assert exit_code == 1
    assert "data" not in payload
    assert "fiscal-year-end" in payload["error"]["message"]
    assert "'FY2026'" in payload["error"]["message"]
    assert payload["error"]["details"][0] == (
        f"{ledger}:2: Failed to parse fava-option entry: Invalid 'fiscal_year_end' option: '06-31'."
    )


@pytest.mark.parametrize("value", ["6-30", "02-30", "garbage"])
@pytest.mark.parametrize("time", ["fiscal_year", "FY2026-Q1", "fy2025 - fy2026", "fiscal_quarter-1"])
def test_every_fiscal_spelling_is_refused_for_every_bad_value(tmp_path: Path, value: str, time: str) -> None:
    exit_code, payload = _json(_ledger(tmp_path, value), "report", "income-statement", "--time", time)

    assert exit_code == 1
    assert f"'{value}'" in payload["error"]["details"][0]


def test_allow_errors_does_not_report_a_calendar_year_as_fiscal(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, "06-31")

    result = runner.invoke(app, ["--file", str(ledger), "report", "income-statement", "-t", "FY2026", "--allow-errors"])

    assert result.exit_code == 1
    assert "2026-01-01 through 2026-12-31" not in result.output
    assert f"{ledger}:2:" in result.output


@pytest.mark.parametrize("command", COMMANDS, ids=COMMAND_IDS)
def test_a_calendar_period_ignores_the_bad_option(tmp_path: Path, command: list[str]) -> None:
    exit_code, payload = _json(_ledger(tmp_path, "06-31"), *command, "--time", "2026")

    assert exit_code == 0
    assert payload["data"]["period"] == {"start": "2026-01-01", "end_exclusive": "2027-01-01"}


def test_a_valid_fiscal_year_end_is_unchanged(tmp_path: Path) -> None:
    exit_code, payload = _json(_ledger(tmp_path, "06-30"), "report", "income-statement", "--time", "FY2026")

    assert exit_code == 0
    assert payload["data"]["period"] == {"start": "2025-07-01", "end_exclusive": "2026-07-01"}
    assert payload["data"]["ledger_valid"] is True
    assert payload["data"]["net_profit"] == {"USD": "-31.00"}
