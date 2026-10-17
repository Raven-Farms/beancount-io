"""A "No position matches" refusal names the posting upstream rejected (w5/510).

The posting was found by account and units only, so selling two lots of
one size named the first, possibly the lot that did match.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Stock HOOL "STRICT"
2024-01-01 open Assets:Cash USD
2024-01-01 open Income:Gains USD
2024-01-05 * "buy"
  Assets:Stock  10 HOOL {100.00 USD}
  Assets:Cash
2024-01-06 * "buy2"
  Assets:Stock  10 HOOL {110.00 USD}
  Assets:Cash
"""
MATCHING = "Assets:Stock -5 HOOL {100.00 USD}"
MISSING = "Assets:Stock -5 HOOL {120.00 USD}"


@pytest.mark.parametrize("order", [(MATCHING, MISSING), (MISSING, MATCHING)], ids=["second", "first"])
def test_the_rejected_lot_is_named(tmp_path: Path, order: tuple[str, str]) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "add", "transaction", "Sell two lots"]
        + ["--date", "2024-03-01", "-p", order[0], "-p", order[1], "-p", "Assets:Cash 1200 USD", "-p", "Income:Gains"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "No position matches -5 HOOL {120.00 USD} in Assets:Stock" in result.stderr
    assert "No position matches -5 HOOL {100.00 USD}" not in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER
