"""`init` writes an exact equity leg, using unsigned zero when balances cancel (w5/310, w5/697).

The sum and its negation ran in the default 28-digit context, so a balance
wider than that got an equity leg rounded to `…345.679`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WIDE = "1234567890123456789012345.678901"


@pytest.mark.parametrize(
    ("balances", "equity"),
    [
        ([f"Assets:Checking -{WIDE}"], WIDE),
        ([f"Assets:Checking {WIDE}"], f"-{WIDE}"),
        ([f"Assets:Checking {WIDE}", "Assets:Cash 0.000001"], "-1234567890123456789012345.678902"),
        pytest.param(["Assets:Cash 20", "Liabilities:CreditCard -20"], "0", id="integer-zero-sum"),
        pytest.param(["Assets:Cash 0.1250", "Liabilities:CreditCard -0.125"], "0", id="fractional-zero-sum"),
        pytest.param(
            ["Assets:Cash 12.50", "Assets:Checking 7.5", "Liabilities:CreditCard -20.000"],
            "0",
            id="mixed-scale-zero-sum",
        ),
        pytest.param(
            [f"Assets:Checking {WIDE}", f"Liabilities:CreditCard -{WIDE}"], "0", id="wide-positive-first-zero-sum"
        ),
        pytest.param(
            [f"Liabilities:CreditCard -{WIDE}", f"Assets:Checking {WIDE}"], "0", id="wide-negative-first-zero-sum"
        ),
    ],
)
def test_the_equity_leg_cancels_every_digit(tmp_path: Path, balances: list[str], equity: str) -> None:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    flags = [arg for balance in balances for arg in ("--opening-balance", balance)]
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "init", "books", "--currency", "USD", "--date", "2026-01-01"]
        + flags,
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    ledger = tmp_path / "books" / "main.bean"
    last = ledger.read_text().splitlines()[-1].split()
    assert last == ["Equity:OpeningBalances", equity, "USD"]
    checked = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--file", str(ledger), "check"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert json.loads(checked.stdout)["data"]["valid"] is True
