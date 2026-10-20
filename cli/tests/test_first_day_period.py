"""A period starting at 0001-01-01 is reported, and BQL `OPEN ON 0001-01-01` names the boundary (w5/842).

Beancount's period clamp transfers and summarizes everything before a period
into the day before it, which 0001-01-01 does not have: `-t 0001` was refused
as an invalid time filter suggesting YYYY, and `OPEN ON 0001-01-01` said only
"date value out of range" for a date that is in range.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    "0001-01-01 open Assets:Cash USD\n0001-01-01 open Expenses:Food USD\n"
    '0001-01-01 * "x"\n  Expenses:Food  5 USD\n  Assets:Cash\n'
)


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "y1.bean"
    path.write_text(LEDGER)
    return path


def test_the_first_year_reports(ledger: Path) -> None:
    result = runner.invoke(app, ["--file", str(ledger), "report", "income-statement", "-t", "0001"])

    assert result.exit_code == 0, result.output
    assert "Income Statement — 0001-01-01 through 0001-12-31" in result.stdout
    assert "Net Profit: -5 USD" in result.stdout


@pytest.mark.parametrize("period", ["0001-01 - 0001-03", "0001", "0001-01"])
def test_a_balance_from_the_first_day_reports(ledger: Path, period: str) -> None:
    result = runner.invoke(app, ["--file", str(ledger), "balance", "-t", period])

    assert result.exit_code == 0, result.output
    assert "Invalid time filter" not in result.output
    assert "5 USD" in result.stdout


def test_open_on_the_first_day_names_the_boundary(ledger: Path) -> None:
    result = runner.invoke(app, ["--file", str(ledger), "query", "SELECT date FROM OPEN ON 0001-01-01"])

    assert result.exit_code == 2, result.output
    said = " ".join(result.stderr.split())
    assert "OPEN ON summarizes everything before its date into the day before it, and 0001-01-01 has none." in said
    assert "Date arithmetic must stay between" not in said


def test_a_later_period_still_summarizes_its_opening(ledger: Path) -> None:
    result = runner.invoke(app, ["--file", str(ledger), "report", "income-statement", "-t", "0002"])

    assert result.exit_code == 0, result.output
    assert "Income Statement — 0002-01-01 through 0002-12-31" in result.stdout
    # Year 1's expense was summarized into the opening, not this year's profit.
    assert "Food                                          —" in result.stdout
