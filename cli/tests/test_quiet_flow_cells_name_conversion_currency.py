"""A quiet interval row's income and expense cells name the conversion currency (w5/268)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Income:Salary USD
2026-01-01 open Expenses:Food USD

2026-01-15 * "Pay"
  Assets:Checking  1000.00 USD
  Income:Salary

2026-03-10 * "Lunch"
  Expenses:Food  10.00 USD
  Assets:Checking
"""
SERIES = ("assets", "liabilities", "income", "expenses")


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
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
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


def _data(tmp_path: Path, kind: str, *extra: str, ledger: str = LEDGER) -> dict[str, Any]:
    (tmp_path / "main.bean").write_text(ledger)
    result = _bea(tmp_path, "--json", "-f", "main.bean", "report", kind, *extra)
    assert result.returncode == 0, result.stderr
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def _text_rows(tmp_path: Path, kind: str, *extra: str) -> dict[str, list[str]]:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea(tmp_path, "-f", "main.bean", "report", kind, *extra)
    assert result.returncode == 0, result.stderr
    rows = [line.split("  ") for line in result.stdout.splitlines() if line.startswith("2026-")]
    return {row[0]: [cell.strip() for cell in row[1:] if cell.strip()] for row in rows}


def test_income_statement_periods_key_income_and_expenses_by_the_currency(tmp_path: Path) -> None:
    periods = {period["date"]: period for period in _data(tmp_path, "income-statement")["periods"]}
    assert periods["2026-01-31"]["income"] == {"USD": "-1000.00"}
    assert periods["2026-01-31"]["expenses"] == {"USD": "0"}
    assert periods["2026-02-28"]["income"] == {"USD": "0"}
    assert periods["2026-02-28"]["expenses"] == {"USD": "0"}
    assert periods["2026-03-10"]["income"] == {"USD": "0"}
    assert periods["2026-03-10"]["expenses"] == {"USD": "10.00"}
    # The control the note names: net profit already read this way.
    assert periods["2026-02-28"]["net_profit"] == {"USD": "0"}


def test_overview_series_name_the_currency_in_every_row(tmp_path: Path) -> None:
    series = _data(tmp_path, "overview")["series"]
    for name in SERIES:
        assert all(list(point["balance"]) == ["USD"] for point in series[name]), name
    by_date = {name: {point["date"]: point["balance"] for point in series[name]} for name in SERIES}
    assert by_date["income"]["2026-02-28"] == {"USD": "0"}
    assert by_date["expenses"]["2026-02-28"] == {"USD": "0"}
    assert by_date["liabilities"]["2026-02-28"] == {"USD": "0"}
    assert by_date["assets"]["2026-02-28"] == {"USD": "1000.00"}
    assert by_date["expenses"]["2026-03-10"] == {"USD": "10.00"}


def test_text_tables_print_zero_in_the_currency_for_a_quiet_month(tmp_path: Path) -> None:
    overview = _text_rows(tmp_path, "overview")
    assert overview["2026-02-28"] == ["1,000.00 USD", "0.00 USD", "0.00 USD", "0.00 USD"]
    statement = _text_rows(tmp_path, "income-statement")
    assert statement["2026-02-28"] == ["0.00 USD", "0.00 USD", "0.00 USD"]
    assert statement["2026-03-10"] == ["0.00 USD", "10.00 USD", "-10.00 USD"]


def test_per_unit_conversion_keeps_quiet_cells_empty(tmp_path: Path) -> None:
    for conversion in ("units", "at_cost", "at_value"):
        periods = {
            period["date"]: period for period in _data(tmp_path, "income-statement", "-x", conversion)["periods"]
        }
        assert periods["2026-02-28"]["income"] == {}, conversion
        assert periods["2026-02-28"]["expenses"] == {}, conversion
        assert periods["2026-01-31"]["expenses"] == {}, conversion
        series = _data(tmp_path, "overview", "-x", conversion)["series"]
        quiet = {name: point["balance"] for name in SERIES for point in series[name] if point["date"] == "2026-02-28"}
        assert quiet == {"assets": {"USD": "1000.00"}, "liabilities": {}, "income": {}, "expenses": {}}, conversion
    assert _text_rows(tmp_path, "overview", "-x", "units")["2026-02-28"] == ["1,000.00 USD", "—", "—", "—"]


def test_unvalued_row_keeps_its_source_commodity(tmp_path: Path) -> None:
    ledger = LEDGER + (
        "2026-01-01 open Assets:Euro EUR\n"
        "2026-01-01 open Expenses:Travel EUR\n"
        '2026-02-10 * "Train"\n'
        "  Expenses:Travel  20.00 EUR\n"
        "  Assets:Euro\n"
    )
    data = _data(tmp_path, "income-statement", "--allow-errors", ledger=ledger)
    periods = {period["date"]: period for period in data["periods"]}
    # A cell that holds something is not quiet: it is not relabelled as zero USD.
    assert periods["2026-02-28"]["expenses"] == {"EUR": "20.00"}
    assert periods["2026-02-28"]["income"] == {"USD": "0"}
    assert periods["2026-02-28"]["net_profit"] == {"USD": None}
