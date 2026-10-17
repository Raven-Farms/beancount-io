"""`add balance --pad-from --json` answers in one model-shaped layout (w5/323).

The branch that wrote both directives returned a raw-namedtuple `directives`
array, `meta` first and Beancount's internal `diff_amount` on the balance, so
`data.directive` was missing exactly when the pad was written.
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
KEYS = {"written", "directive", "pad", "duplicate", "source", "warnings"}
OPENING = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening
2026-01-02 * "Open"
  Assets:Checking  100.00 USD
  Equity:Opening
"""
EXISTING_PAD = """option "operating_currency" "USD"
2026-01-01 open Assets:Bank:Checking USD,EUR
2026-01-01 open Equity:Opening
2026-01-01 open Income:Salary
2026-01-05 * "Pay"
  Assets:Bank:Checking  1000.00 USD
  Income:Salary
2026-01-10 * "Euro"
  Assets:Bank:Checking  50 EUR
  Equity:Opening
2026-02-28 pad Assets:Bank:Checking Equity:Opening
2026-03-01 balance Assets:Bank:Checking  2000 USD
"""


def _bea(tmp_path: Path, ledger: Path, *args: str) -> Any:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(ledger), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["data"]


@pytest.mark.parametrize(
    ("ledger_text", "account", "amount", "written"),
    [
        (OPENING, "Assets:Checking", "800 ~ 0.01 USD", 2),
        (OPENING, "Assets:Checking", "100.00 USD", 1),
        (EXISTING_PAD, "Assets:Bank:Checking", "200 EUR", 1),
    ],
    ids=["pad-written", "already-matches", "existing-pad"],
)
def test_every_branch_has_one_layout(tmp_path: Path, ledger_text: str, account: str, amount: str, written: int) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(ledger_text)
    date = "2026-03-01" if ledger_text is EXISTING_PAD else "2026-03-07"
    data = _bea(
        tmp_path,
        ledger,
        "add",
        "balance",
        "--date",
        date,
        "-a",
        account,
        "--amount",
        amount,
        "--pad-from",
        "Equity:Opening",
    )

    assert set(data) == KEYS
    assert data["written"] == written
    assert "diff_amount" not in json.dumps(data)
    balances = _bea(tmp_path, ledger, "list", "balance")
    assert data["directive"] in balances
    if written == 2:
        # The model shape `list pad` uses, plus what this pad inserts (w5/611).
        pad = dict(data["pad"])
        assert pad.pop("amount") == {"number": "700.00", "currency": "USD"}
        assert pad in _bea(tmp_path, ledger, "list", "pad")
    else:
        assert data["pad"] is None
