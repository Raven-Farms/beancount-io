"""Report and balance trees keep one amount column for wide account names (w5/149).

The tree label was padded with `str.format`, which counts code points, so an
account component in CJK characters, two terminal columns each, pushed its
amount to the right of every other row's.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from cli import output

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Bank:Checking USD
2026-01-01 open Assets:Bank:Épargne USD
2026-01-01 open Assets:Bank:X現金口座 USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "open"
  Assets:Bank:Checking  3000.00 USD
  Assets:Bank:Épargne  2000.00 USD
  Assets:Bank:X現金口座  1000.00 USD
  Equity:Opening
"""
# Two spaces of margin, a 46-column label, two spaces of gutter.
AMOUNT_COLUMN = 50
AMOUNTS = {"Checking": "3,000.00 USD", "Épargne": "2,000.00 USD", "X現金口座": "1,000.00 USD"}


def _bea(tmp_path: Path, *args: str) -> str:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONIOENCODING="utf-8",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _row(stdout: str, label: str) -> str:
    rows = [line for line in stdout.splitlines() if line.strip().startswith(label)]
    assert len(rows) == 1, stdout
    return rows[0]


@pytest.mark.parametrize("command", [["report", "balance-sheet"], ["report", "trial-balance"], ["balance"]])
def test_every_tree_row_starts_its_amount_in_the_same_column(tmp_path: Path, command: list[str]) -> None:
    stdout = _bea(tmp_path, *command)

    for label, amount in AMOUNTS.items():
        row = _row(stdout, label)
        assert row.endswith(amount), row
        assert output.display_width(row.removesuffix(amount)) == AMOUNT_COLUMN, row


@pytest.mark.parametrize("command", [["report", "balance-sheet"], ["report", "trial-balance"], ["balance"]])
def test_narrow_account_rows_keep_their_bytes(tmp_path: Path, command: list[str]) -> None:
    stdout = _bea(tmp_path, *command)

    assert _row(stdout, "Checking") == "      Checking" + " " * 36 + "3,000.00 USD"
    assert _row(stdout, "Épargne") == "      Épargne" + " " * 37 + "2,000.00 USD"
    assert _row(stdout, "Assets") == "  Assets" + " " * 42 + "6,000.00 USD"
