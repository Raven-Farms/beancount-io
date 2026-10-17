"""`report -a NAME` matches that account and its children, never the same components deeper in a name (w5/616).

w5/292 switched account-name values to Beancount's `has_component`, which
searches for the components anywhere: `-a Expenses:Travel` also took
`Assets:Reimbursable:Expenses:Travel` into net worth. A bare root was read
as a pattern: `-a Income` pulled `Expenses:Taxes:Income` into net profit.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
REIMBURSABLE = """option "operating_currency" "USD"
2026-01-01 open Assets:Bank USD
2026-01-01 open Assets:Reimbursable:Expenses:Travel USD
2026-01-01 open Expenses:Travel USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "fund"
  Assets:Bank  1000.00 USD
  Equity:Opening
2026-01-10 * "own trip"
  Expenses:Travel  100.00 USD
  Assets:Bank
2026-01-12 * "work trip"
  Assets:Reimbursable:Expenses:Travel  400.00 USD
  Assets:Bank
"""
TAXED = """option "operating_currency" "USD"
2026-01-01 open Assets:Bank USD
2026-01-01 open Income:Salary USD
2026-01-01 open Expenses:Taxes:Income USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "pay"
  Assets:Bank  700.00 USD
  Expenses:Taxes:Income  300.00 USD
  Income:Salary  -1000.00 USD
2026-01-06 * "food"
  Expenses:Food  50.00 USD
  Assets:Bank
"""


def _report(tmp_path: Path, text: str, *args: str) -> dict[str, object]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(text)
    result = runner.invoke(app, ["--json", "-f", str(ledger), "report", *args])
    assert result.exit_code == 0, result.output
    data: dict[str, object] = json.loads(result.stdout)["data"]
    return data


def test_an_account_name_keeps_its_own_subtree_only(tmp_path: Path) -> None:
    data = _report(tmp_path, REIMBURSABLE, "balance-sheet", "-a", "Expenses:Travel")

    assert "Reimbursable" not in json.dumps(data)
    assert data["net_worth"] in ({}, {"USD": "0.00"}, {"USD": "0"})


def test_a_bare_root_is_anchored(tmp_path: Path) -> None:
    data = _report(tmp_path, TAXED, "income-statement", "-a", "Income")

    assert data["net_profit"] == {"USD": "1000.00"}
    assert "Taxes" not in json.dumps(data)


def test_a_pattern_still_searches(tmp_path: Path) -> None:
    data = _report(tmp_path, TAXED, "income-statement", "-a", "food")

    assert data["net_profit"] == {"USD": "-50.00"}
