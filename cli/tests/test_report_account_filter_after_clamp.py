"""`report -a Equity -t PERIOD` keeps the equity the period's clamp synthesizes (w5/501).

Fava filtered by account before the time clamp, so the clamp summarized only
the filtered transactions: `-a Equity -t 2025` showed -1,000 where the whole
report and `bea balance` showed -4,000, and `-a Equity:Earnings` matched
nothing. A currency conversion lost `Equity:Conversions:Current` the same way.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EARNINGS = """option "operating_currency" "USD"

2024-01-01 open Assets:Bank USD
2024-01-01 open Equity:Opening-Balances
2024-01-01 open Income:Salary USD

2024-01-01 * "Opening"
  Assets:Bank 1000.00 USD
  Equity:Opening-Balances

2024-06-30 * "Salary"
  Assets:Bank 3000.00 USD
  Income:Salary

2025-03-01 * "Salary"
  Assets:Bank 100.00 USD
  Income:Salary
"""
EXCHANGE = """option "operating_currency" "USD"
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Euro EUR
2024-01-01 open Equity:Opening-Balances
2024-01-01 open Expenses:Food
2024-01-01 * "Opening"
  Assets:Bank 1000.00 USD
  Equity:Opening-Balances
2024-01-10 * "Exchange"
  Assets:Euro 100.00 EUR @ 1.10 USD
  Assets:Bank -110.00 USD
2024-02-05 * "Exchange"
  Assets:Euro 50.00 EUR @ 1.20 USD
  Assets:Bank -60.00 USD
2024-02-06 * "Lunch"
  Expenses:Food 10.00 EUR
  Assets:Euro
"""


def _report(tmp_path: Path, ledger: str, *args: str) -> dict[str, Any]:
    (tmp_path / "main.bean").write_text(ledger)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), "report", "trial-balance"]
        + list(args),
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return dict(json.loads(result.stdout)["data"])


def _balances(node: dict[str, Any] | None) -> dict[str, Any]:
    """Each account in a report tree with its subtree balance."""
    if not node:
        return {}
    found = {node["account"]: node["balance_children"]}
    for child in node.get("children") or []:
        found.update(_balances(child))
    return found


@pytest.mark.parametrize(
    ("ledger", "args"),
    [(EARNINGS, ("-t", "2025")), (EXCHANGE, ("-t", "2024-02", "-x", "units"))],
    ids=["previous-earnings", "conversions"],
)
def test_the_filtered_equity_is_the_whole_reports_equity(tmp_path: Path, ledger: str, args: tuple[str, ...]) -> None:
    whole = _report(tmp_path, ledger, *args)
    filtered = _report(tmp_path, ledger, *args, "-a", "Equity")

    assert _balances(filtered["equity"]) == _balances(whole["equity"])
    assert _balances(whole["equity"])  # the fixture has equity to compare


def test_previous_earnings_alone_is_found(tmp_path: Path) -> None:
    filtered = _report(tmp_path, EARNINGS, "-t", "2025", "-a", "Equity:Earnings")

    assert filtered["account_filter_empty"] is False
    assert _balances(filtered["equity"])["Equity:Earnings:Previous"] == {"USD": "-3000.00"}
    assert _balances(filtered["equity"])["Equity"] == {"USD": "-3000.00"}
