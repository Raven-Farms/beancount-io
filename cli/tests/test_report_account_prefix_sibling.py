"""`report --account Expenses:Food` means that account and its children (w5/292).

`--account` documents "a parent account or a regular expression". Every account
name is also a valid regex, and the filter used an unanchored search, so a plain
parent name picked up prefix siblings: `Assets:Bank` counted `Assets:Bankroll`
and `Expenses:Food` counted `Expenses:FoodTruck`, in the trees, the totals and
the net profit. A value spelled as an account name now matches by component;
patterns and single words keep the regular-expression search.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Bank USD
2026-01-01 open Assets:Bankroll USD
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Expenses:Food:Dining USD
2026-01-01 open Expenses:FoodTruck USD
2026-01-01 open Equity:Opening USD

2026-01-02 * "Open"
  Assets:Bank  100.00 USD
  Assets:Bankroll  50.00 USD
  Assets:Cash  10.00 USD
  Equity:Opening

2026-01-05 * "Meal"
  Expenses:Food:Dining  7.00 USD
  Expenses:FoodTruck  3.00 USD
  Assets:Bank
"""


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
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
        timeout=120,
        check=False,
    )


def _accounts(node: dict | None) -> set[str]:
    if not node:
        return set()
    found = {node["account"]}
    for child in node.get("children", []):
        found |= _accounts(child)
    return found


def test_parent_account_excludes_its_prefix_sibling(tmp_path: Path, ledger: Path) -> None:
    result = _bea(tmp_path, "--json", "-f", str(ledger), "report", "income-statement", "-a", "Expenses:Food")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["data"]
    assert data["net_profit"] == {"USD": "-7.00"}
    assert "Expenses:FoodTruck" not in _accounts(data["expenses"])
    assert "Expenses:Food:Dining" in _accounts(data["expenses"])


def test_balance_sheet_parent_filter_drops_the_sibling_row(tmp_path: Path, ledger: Path) -> None:
    result = _bea(tmp_path, "-f", str(ledger), "report", "balance-sheet", "-a", "Assets:Bank")
    assert result.returncode == 0, result.stderr
    assert "Bankroll" not in result.stdout
    assert "90.00 USD" in result.stdout


def test_an_anchored_regex_and_a_bare_word_keep_regex_search(tmp_path: Path, ledger: Path) -> None:
    pattern = _bea(tmp_path, "--json", "-f", str(ledger), "report", "income-statement", "-a", "Expenses:Food.*")
    assert pattern.returncode == 0, pattern.stderr
    assert json.loads(pattern.stdout)["data"]["net_profit"] == {"USD": "-10.00"}

    word = _bea(tmp_path, "--json", "-f", str(ledger), "report", "income-statement", "-a", "food")
    assert word.returncode == 0, word.stderr
    assert json.loads(word.stdout)["data"]["net_profit"] == {"USD": "-10.00"}
