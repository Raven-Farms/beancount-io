"""Report series classify accounts by root component, not by text prefix (w5/921).

With `name_income` `Earnings` and `name_equity` `EarningsCapital`, the series
helpers took equity for income (period profit 125 instead of 20), and with
assets `Capital` and equity `CapitalEquity`, the net-worth series erased an
opening balance, while the headlines and the trees stayed right.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from tests.test_import_source_facts import _bea

INCOME = """option "operating_currency" "USD"
option "name_income" "Earnings"
option "name_equity" "EarningsCapital"
2020-01-01 open Assets:Cash USD
2020-01-01 open Earnings:Salary USD
2020-01-01 open EarningsCapital:Opening USD
2020-03-01 * "Opening"
  Assets:Cash 100 USD
  EarningsCapital:Opening -100 USD
2020-03-02 * "Salary"
  Assets:Cash 20 USD
  Earnings:Salary -20 USD
2020-03-30 * "Capital"
  Assets:Cash 5 USD
  EarningsCapital:Opening -5 USD
2020-03-31 price HOOL 10 USD
"""
WORTH = """option "operating_currency" "USD"
option "name_assets" "Capital"
option "name_equity" "CapitalEquity"
2024-01-01 open Capital:Cash USD
2024-01-01 open CapitalEquity:Opening USD
2024-01-02 * "Opening"
  Capital:Cash 100 USD
  CapitalEquity:Opening -100 USD
"""


def _report(tmp_path: Path, ledger: str, *args: str) -> dict[str, Any]:
    (tmp_path / "main.bean").write_text(ledger)
    result = _bea(tmp_path, "report", *args)
    assert result.returncode == 0, result.stderr
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def _number(value: dict[str, Any], currency: str = "USD") -> Decimal:
    return Decimal(str(value.get(currency, 0)))


def test_the_monthly_profit_breakdown_agrees_with_the_headline(tmp_path: Path) -> None:
    data = _report(tmp_path, INCOME, "income-statement", "--time", "2020-03", "--interval", "monthly")

    (period,) = data["periods"]
    assert _number(period["income"]) == Decimal("-20") == _number(data["income"]["balance_children"])
    assert _number(period["net_profit"]) == Decimal("20") == _number(data["net_profit"])


def test_capital_only_weekly_fragments_are_not_income_weeks(tmp_path: Path) -> None:
    data = _report(tmp_path, INCOME, "income-statement", "--time", "2020-03", "--interval", "weekly")

    periods = {point["date"]: _number(point["income"]) for point in data["periods"]}
    assert periods["2020-03-08"] == Decimal("-20")
    assert sum(periods.values()) == Decimal("-20")
    # The trailing 30–31 March fragment holds only capital and a price directive.
    assert "2020-03-31" not in periods and "2020-04-05" not in periods


def test_the_net_worth_series_keeps_an_opening_under_a_prefixed_equity_root(tmp_path: Path) -> None:
    data = _report(tmp_path, WORTH, "balance-sheet", "--time", "2024-01", "--interval", "monthly")

    assert _number(data["net_worth"]) == Decimal("100")
    assert [(point["date"], _number(point["balance"])) for point in data["net_worth_series"]] == [
        ("2024-01-31", Decimal("100"))
    ]
