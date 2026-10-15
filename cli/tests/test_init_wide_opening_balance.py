"""`init` writes the equity leg as the exact negation of wide opening balances (w5/310).

The sum and its negation ran in the default 28-digit context, so a balance
wider than that got an equity leg rounded to `…345.679`.
"""

from __future__ import annotations

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
    ],
)
def test_the_equity_leg_cancels_every_digit(tmp_path: Path, balances: list[str], equity: str) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
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
    last = (tmp_path / "books" / "main.bean").read_text().splitlines()[-1].split()
    assert last == ["Equity:OpeningBalances", equity, "USD"]
