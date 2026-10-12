"""A report's balance series count every transaction its headline counts (w5/083).

The vendored series generators skipped `U`-flagged transactions — a flag
`bea add transaction --flag U` accepts — so one report showed two net worths
for the same date: the headline with the entry, the series without it.
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
2024-01-01 open Assets:Checking USD
2024-01-01 open Equity:Opening
2024-01-01 open Income:Salary
2024-01-01 open Expenses:Food

2024-01-01 * "Opening balance"
  Assets:Checking  1000.00 USD
  Equity:Opening

2024-02-10 {flag} "Employer" "Salary, uncleared"
  Assets:Checking  500.00 USD
  Income:Salary

2024-03-05 * "Grocer" "Food"
  Expenses:Food  40.00 USD
  Assets:Checking
"""
EXPECTED = ["1000.00", "1500.00", "1460.00"]


def _report(tmp_path: Path, flag: str, kind: str, *args: str, as_json: bool = True) -> Any:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(flag=flag))
    result = runner.invoke(
        app, [*(["--json"] if as_json else []), "--file", str(ledger), "report", kind, "-t", "2024-Q1", *args]
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"] if as_json else result.output


@pytest.mark.parametrize("flag", ["U", "!", "*", "A"])
def test_the_last_net_worth_point_equals_the_headline(tmp_path: Path, bea_config_dir: Path, flag: str) -> None:
    data = _report(tmp_path, flag, "balance-sheet")

    assert data["net_worth"] == {"USD": "1460.00"}
    assert [point["balance"]["USD"] for point in data["net_worth_series"]] == EXPECTED
    assert data["net_worth_series"][-1]["balance"] == data["net_worth"]


@pytest.mark.parametrize("flag", ["U", "!"])
def test_the_overview_asset_series_moves_with_the_income_it_reports(
    tmp_path: Path, bea_config_dir: Path, flag: str
) -> None:
    series = _report(tmp_path, flag, "overview")["series"]

    assert [point["balance"]["USD"] for point in series["assets"]] == EXPECTED
    assert series["income"][1]["balance"] == {"USD": "-500.00"}


def test_an_account_filtered_series_includes_the_entry_too(tmp_path: Path, bea_config_dir: Path) -> None:
    data = _report(tmp_path, "U", "balance-sheet", "--account", "Assets:Checking")

    assert [point["balance"]["USD"] for point in data["net_worth_series"]] == EXPECTED


def test_the_text_report_prints_one_net_worth_for_the_period_end(tmp_path: Path, bea_config_dir: Path) -> None:
    text = _report(tmp_path, "U", "balance-sheet", as_json=False)

    assert "Net Worth: 1,460.00 USD" in " ".join(text.split())
    assert "960.00 USD" not in text.replace("1,460.00 USD", "")
