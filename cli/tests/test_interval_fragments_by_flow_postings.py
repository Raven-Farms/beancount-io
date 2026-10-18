"""A clipped boundary fragment is kept only when a transaction in it posts to the flow accounts (w5/617).

The quiet-fragment test ignored every entry from a `<…>` source, not only
the time-filter clamp's own, so a plugin's transaction on the last day was
dropped (weekly rows summed to 960 under a 965 headline). It also counted
any directive, so a month-end balance assertion kept an empty one-day row.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
{plugin}2026-01-01 open Assets:Cash USD
2026-01-01 open Income:Salary USD
2026-01-01 open Income:Interest USD
2026-01-01 open Expenses:Food USD
2026-03-05 * "food"
  Expenses:Food  40.00 USD
  Assets:Cash
2026-03-20 * "pay"
  Assets:Cash  1000.00 USD
  Income:Salary
{extra}"""
ACCRUE = """\
import datetime
from decimal import Decimal
from beancount.core import amount, data

__plugins__ = ["accrue"]


def accrue(entries, options_map):
    meta = data.new_metadata("<accrue>", 0)
    accrual = data.Transaction(meta, datetime.date(2026, 3, 31), "*", None, "interest accrual", frozenset(),
                               frozenset(), [
        data.Posting("Assets:Cash", amount.Amount(Decimal("5.00"), "USD"), None, None, None, None),
        data.Posting("Income:Interest", amount.Amount(Decimal("-5.00"), "USD"), None, None, None, None),
    ])
    return entries + [accrual], []
"""


def _weekly(tmp_path: Path, text: str) -> dict[str, Any]:
    (tmp_path / "main.bean").write_text(text)
    (tmp_path / "accrue.py").write_text(ACCRUE)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(tmp_path)]),
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean")]
        + ["report", "income-statement", "-t", "2026-03", "-i", "weekly"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def test_a_plugin_transaction_on_the_last_day_keeps_its_row(tmp_path: Path) -> None:
    data = _weekly(tmp_path, LEDGER.format(plugin='plugin "accrue"\n', extra=""))

    periods = data["periods"]
    assert [period["date"] for period in periods] == [
        "2026-03-08",
        "2026-03-15",
        "2026-03-22",
        "2026-03-29",
        "2026-03-31",
    ]
    assert periods[-1]["net_profit"] == {"USD": "5.00"}
    assert sum(float(period["net_profit"].get("USD", 0)) for period in periods) == 965.0
    assert data["net_profit"] == {"USD": "965.00"}


def test_balance_assertions_alone_keep_no_empty_rows(tmp_path: Path) -> None:
    extra = "2026-03-01 balance Assets:Cash 0 USD\n2026-03-31 balance Assets:Cash 960 USD\n"

    data = _weekly(tmp_path, LEDGER.format(plugin="", extra=extra))

    assert [period["date"] for period in data["periods"]] == ["2026-03-08", "2026-03-15", "2026-03-22", "2026-03-29"]
