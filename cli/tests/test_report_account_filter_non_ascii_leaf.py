"""`report -a` with a CJK or Thai leaf matches that account and its children only (w5/829).

The filter treated a value as an account name only when `is_valid` accepted it;
`Expenses:Food:中餐` and `Expenses:Kค่า` load but fail that regex, so they fell
through to an unanchored search and pulled in `Expenses:Food:中餐厅` and
`Expenses:Kค่าX`: wrong totals, exit 0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
SPENT = {"Expenses:Food:中餐": "5.00", "Expenses:Food:中餐厅": "7.00", "Expenses:Kค่า": "2.00", "Expenses:Kค่าX": "3.00"}
SPENT_ASCII = {"Expenses:Food": "4.00", "Expenses:FoodTruck": "6.00"}


def _ledger(tmp_path: Path, spent: dict[str, str]) -> Path:
    lines = ['option "operating_currency" "USD"', "2024-01-01 open Assets:Bank USD"]
    lines += [f"2024-01-01 open {name} USD" for name in spent]
    for day, (name, amount) in enumerate(spent.items(), start=1):
        lines += [f'2024-02-{day:02d} * "spend"', f"  {name}  {amount} USD", "  Assets:Bank"]
    path = tmp_path / "main.bean"
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.mark.parametrize(
    ("spent", "account", "profit"),
    [
        (SPENT, "Expenses:Food:中餐", "-5.00"),
        (SPENT, "Expenses:Kค่า", "-2.00"),
        (SPENT_ASCII, "Expenses:Food", "-4.00"),
    ],
    ids=["cjk", "thai", "ascii-control"],
)
def test_the_filter_keeps_the_account_and_its_children(
    tmp_path: Path, spent: dict[str, str], account: str, profit: str
) -> None:
    ledger = _ledger(tmp_path, spent)

    result = runner.invoke(app, ["--json", "--file", str(ledger), "report", "income-statement", "-a", account])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"]["net_profit"] == {"USD": profit}
