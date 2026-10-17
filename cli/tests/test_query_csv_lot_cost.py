"""CSV query output keeps a lot's cost date and label (w5/465).

Two lots bought at the same price rendered as the same `10 HOOL {100 USD}`
cell, though `--json` kept their dates and labels apart.
"""

from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = r"""option "operating_currency" "USD"
2026-01-01 open Assets:Brk
2026-01-01 open Assets:Cash USD
2026-01-03 * "Buy"
  Assets:Brk 10 HOOL {100 USD, 2026-01-03, "lotA"}
  Assets:Cash -1000 USD
2026-01-06 * "Buy B"
  Assets:Brk 10 HOOL {100 USD, 2026-01-06, "lotB"}
  Assets:Cash -1000 USD
2026-01-07 * "Buy C"
  Assets:Brk 1 HOOL {100 USD, "say \"hi\""}
  Assets:Cash -100 USD
"""
LOT_A = '10 HOOL {100 USD, 2026-01-03, "lotA"}'
LOT_B = '10 HOOL {100 USD, 2026-01-06, "lotB"}'
LOT_C = r'1 HOOL {100 USD, 2026-01-07, "say \"hi\""}'


def _query(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "lots.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "lots.bean"), "query", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_csv_positions_keep_each_lots_date_and_label(tmp_path: Path) -> None:
    result = _query(tmp_path, "-o", str(tmp_path / "lots.csv"), "SELECT date, position WHERE account = 'Assets:Brk'")
    assert result.returncode == 0, result.stderr
    rows = list(csv.reader(io.StringIO((tmp_path / "lots.csv").read_text())))
    assert [row[1] for row in rows[1:]] == [LOT_A, LOT_B, LOT_C]


def test_csv_inventories_keep_lots_distinct(tmp_path: Path) -> None:
    result = _query(
        tmp_path,
        "--format",
        "csv",
        "SELECT account, sum(position) AS s WHERE account = 'Assets:Brk' GROUP BY account",
    )
    assert result.returncode == 0, result.stderr
    rows = list(csv.reader(io.StringIO(result.stdout)))
    assert rows[1] == ["Assets:Brk", f"{LOT_A}, {LOT_B}, {LOT_C}"]


def test_a_bare_cost_column_keeps_each_lots_date_and_label(tmp_path: Path) -> None:
    """`position.cost` is a lot without its units, rendered as bean-query writes it (w5/561)."""
    result = _query(tmp_path, "-f", "csv", "SELECT date, position.cost WHERE account = 'Assets:Brk'")

    assert result.returncode == 0, result.stderr
    rows = list(csv.reader(io.StringIO(result.stdout)))
    assert [row[1] for row in rows[1:]] == [
        '100 USD, 2026-01-03, "lotA"',
        '100 USD, 2026-01-06, "lotB"',
        r'100 USD, 2026-01-07, "say \"hi\""',
    ]
    # A cost-less posting has no lot: the cell stays empty, and amounts keep their plain form.
    cash = _query(tmp_path, "-f", "csv", "SELECT position.cost, position.units WHERE account = 'Assets:Cash'")
    assert list(csv.reader(io.StringIO(cash.stdout)))[1] == ["", "-1000 USD"]
