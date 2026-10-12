"""A quiet trailing interval fragment is dropped even when the period holds a currency exchange (w5/086).

Clamping the ledger to `--time` synthesizes a `C "Conversion for (…)"`
transaction on the period's last day whenever the period holds a priced
exchange, so the fragment always looked as if it contained an entry and the
flow series kept one extra all-zero row.
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
2024-01-01 open Assets:Bank
2024-01-01 open Assets:Euro
2024-01-01 open Equity:Open
2024-01-01 open Expenses:Food

2024-01-01 * "Open"
  Assets:Bank  1000.00 USD
  Equity:Open

2024-01-02 price EUR 1.10 USD

2024-01-15 * "Buy EUR"
  {exchange}
  Assets:Bank  -110.00 USD

2024-01-16 * "Lunch"
  Expenses:Food  12.00 USD
  Assets:Bank
"""
EXCHANGE = "Assets:Euro  100.00 EUR @ 1.10 USD"
SAME_CURRENCY = "Assets:Euro  110.00 USD"
WEEKS = ["2024-01-07", "2024-01-14", "2024-01-21", "2024-01-28"]


def _report(tmp_path: Path, kind: str, *args: str, exchange: str = EXCHANGE, extra: str = "") -> Any:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(exchange=exchange) + extra)
    result = runner.invoke(app, ["--json", "--file", str(ledger), "report", kind, *args])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


@pytest.mark.parametrize("exchange", [EXCHANGE, SAME_CURRENCY], ids=["priced-exchange", "single-currency"])
def test_a_quiet_weekly_fragment_is_dropped(tmp_path: Path, bea_config_dir: Path, exchange: str) -> None:
    data = _report(tmp_path, "income-statement", "-t", "2024-01", "-i", "weekly", exchange=exchange)

    assert [period["date"] for period in data["periods"]] == WEEKS


def test_the_text_report_prints_four_rows(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(exchange=EXCHANGE))

    result = runner.invoke(app, ["--file", str(ledger), "report", "income-statement", "-t", "2024-01", "-i", "weekly"])

    assert result.exit_code == 0, result.output
    rows = [line.split()[0] for line in result.output.splitlines() if line[:5] == "2024-"]
    assert rows == WEEKS


def test_a_quiet_fragment_of_another_interval_is_dropped_too(tmp_path: Path, bea_config_dir: Path) -> None:
    data = _report(tmp_path, "income-statement", "-t", "2024-01-01 - 2024-02-10", "-i", "monthly")

    assert [period["date"] for period in data["periods"]] == ["2024-01-31"]


def test_a_fragment_holding_a_real_entry_on_the_last_day_is_kept(tmp_path: Path, bea_config_dir: Path) -> None:
    late = '\n2024-01-31 * "Late snack"\n  Expenses:Food  3.00 USD\n  Assets:Bank\n'

    data = _report(tmp_path, "income-statement", "-t", "2024-01", "-i", "weekly", extra=late)

    assert [period["date"] for period in data["periods"]] == [*WEEKS, "2024-01-31"]


def test_balance_series_keep_every_bucket(tmp_path: Path, bea_config_dir: Path) -> None:
    data = _report(tmp_path, "balance-sheet", "-t", "2024-01", "-i", "weekly")

    assert [point["date"] for point in data["net_worth_series"]] == [*WEEKS, "2024-01-31"]
