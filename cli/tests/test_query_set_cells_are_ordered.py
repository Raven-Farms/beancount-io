"""Set-valued query cells print in one order whatever the hash seed (w5/105).

`tags`, `links` and `other_accounts` were emitted in Python hash order in
`--json` and `-f csv` output, so the same command on the same ledger produced
different bytes from one run to the next.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food
2024-01-01 open Expenses:Travel
2024-01-01 open Expenses:Tips
2024-01-05 * "Grocer" "Refund" #food #trip #reimbursable #zeta #alpha ^receipt-9 ^claim-2 ^batch-7
  Expenses:Food    -5.00 USD
  Expenses:Travel  -2.00 USD
  Expenses:Tips    -1.00 USD
  Assets:Cash
"""
SEEDS = ["1", "2", "3", "7", "11"]


def _bea(tmp_path: Path, seed: str, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONHASHSEED=seed,
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize(
    ("column", "expected"),
    [
        ("tags", ["alpha", "food", "reimbursable", "trip", "zeta"]),
        ("links", ["batch-7", "claim-2", "receipt-9"]),
        ("other_accounts", ["Expenses:Food", "Expenses:Tips", "Expenses:Travel"]),
    ],
)
def test_json_and_csv_cells_are_sorted_under_every_seed(tmp_path: Path, column: str, expected: list[str]) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    query = f"SELECT {column} WHERE account = 'Assets:Cash'"

    as_json = {seed: _bea(tmp_path, seed, "--json", "query", query) for seed in SEEDS}
    as_csv = {seed: _bea(tmp_path, seed, "query", "-f", "csv", query) for seed in SEEDS}

    assert len(set(as_json.values())) == 1, as_json
    assert len(set(as_csv.values())) == 1, as_csv
    assert json.loads(as_json["1"])["data"]["rows"] == [[expected]]
    assert ", ".join(expected) in as_csv["1"]
