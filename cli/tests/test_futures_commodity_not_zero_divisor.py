"""A futures commodity such as `/0J` is a currency, not a division by zero (w5/489).

The zero-divisor pre-check read `/0` followed by a letter as a zero divisor,
so `1 /0J {100 USD}` was refused in `add` postings, balances and bulk rows.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from bea_engine.amounts import refuse_zero_divisor
from cli.amounts import check_decimal_notation
from cli.errors import UsageError

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("text", ["Assets:Brokerage 1 /0J {100 USD}", "1 /0J", "2 /00Z26", "1 /0'X"])
def test_a_slash_currency_is_not_a_divisor(text: str) -> None:
    check_decimal_notation(text)
    refuse_zero_divisor(text)


@pytest.mark.parametrize("text", ["1 / 0 USD", "1/0 USD", "(1/0.0) USD", "10 / -0"])
def test_a_real_zero_divisor_is_still_refused(text: str) -> None:
    with pytest.raises(UsageError):
        check_decimal_notation(text)
    with pytest.raises(ValueError):
        refuse_zero_divisor(text)


def test_add_writes_a_futures_posting_and_balance(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Brokerage\n2026-01-01 open Assets:Cash\n'
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )

    def bea(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "cli.main", "-f", str(ledger), *args],
            cwd=tmp_path,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    posted = bea(
        "add", "transaction", "F", "--date", "2026-01-05", "-p", "Assets:Brokerage 1 /0J {100 USD}", "-p", "Assets:Cash"
    )
    assert posted.returncode == 0, posted.stderr
    asserted = bea("add", "balance", "--date", "2026-01-06", "-a", "Assets:Brokerage", "--amount", "1 /0J")
    assert asserted.returncode == 0, asserted.stderr
    assert "1 /0J {100 USD}" in ledger.read_text()
    assert bea("check").returncode == 0
