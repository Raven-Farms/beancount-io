"""An account filter that is no account and no regular expression exits 2 (w5/502).

The filter fell back to plain equality and to a component wrapper that read
`*Food*` as "component Foo, then d*": the report dropped Expenses:FoodTruck
with exit 0, and compile errors quoted positions the user never typed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Expenses:FoodTruck USD
2024-01-01 open Equity:Opening-Balances USD
2024-01-02 * "o"
  Assets:Bank 100.00 USD
  Equity:Opening-Balances
2024-01-03 * "f"
  Expenses:Food 10.00 USD
  Assets:Bank
2024-01-04 * "t"
  Expenses:FoodTruck 7.00 USD
  Assets:Bank
"""


def _report(tmp_path: Path, pattern: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "food.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "-f",
            str(tmp_path / "food.bean"),
            "report",
            "income-statement",
            "-a",
            pattern,
        ],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("pattern", "reason"),
    [
        ("*Food*", "nothing to repeat at position 0"),
        ("*Food", "nothing to repeat at position 0"),
        ("\\1", "invalid group reference 1 at position 1"),
        ("Fo)(od", "unbalanced parenthesis at position 2"),
        ("\\", "bad escape (end of pattern) at position 0"),
    ],
)
def test_an_invalid_pattern_is_refused_with_its_own_position(tmp_path: Path, pattern: str, reason: str) -> None:
    result = _report(tmp_path, pattern)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"Invalid account filter {pattern!r}: {reason}." in result.stderr


@pytest.mark.parametrize(
    ("pattern", "profit"),
    [(".*Food.*", "-17.00 USD"), ("food", "-17.00 USD"), ("Expenses:Food", "-10.00 USD")],
)
def test_valid_filters_are_unchanged(tmp_path: Path, pattern: str, profit: str) -> None:
    result = _report(tmp_path, pattern)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Net Profit: {profit}" in result.stdout
