"""`doctor region --conversion` shows converted balances at their own precision (w5/498).

The tree's display context learned precision from posting units only, so a
holding valued at 101.55 printed `1016 USD` over `Net Income: (15.50 USD)`,
and a cost of `33.3333 USD` printed `100.00 USD` over `-99.9999 USD`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOLDING = """2024-01-01 open Assets:Broker HOOL
2024-01-01 open Assets:Cash USD

2024-01-02 * "Buy"
  Assets:Broker  10 HOOL {100 USD}
  Assets:Cash   -1000 USD

2024-01-03 price HOOL 101.55 USD
"""
GIFT = """2024-01-01 open Expenses:Gift
2024-01-01 open Assets:Cash USD
2024-01-02 * "Gift"
  Expenses:Gift  3 HOOL {33.3333 USD}
  Assets:Cash   -100.00 USD
"""


@pytest.mark.parametrize(
    ("ledger", "region", "conversion", "shown"),
    [
        (HOLDING, "4:6", "value", ["Broker                  1015.50 USD", "Unrealized           -15.50 USD"]),
        (GIFT, "1:5", "cost", ["Gift           99.9999 USD"]),
    ],
    ids=["value", "cost"],
)
def test_the_tree_agrees_with_net_income(
    tmp_path: Path, ledger: str, region: str, conversion: str, shown: list[str]
) -> None:
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
        [sys.executable, "-m", "cli.main", "doctor", "region", str(tmp_path / "main.bean"), region]
        + ["--conversion", conversion],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for line in shown:
        assert line in result.stdout
