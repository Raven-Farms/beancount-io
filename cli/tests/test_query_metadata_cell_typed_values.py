"""A metadata cell is the JSON output's object, not a Python repr (w5/230).

Selecting a whole metadata dictionary printed `str()` of it in CSV and in the
text table: `Decimal('1E-8')`, `datetime.date(2026, 1, 7)`, `True`. Nothing can
parse that, and the tiny rate carried the exponent query output never uses.
The cell is now the object `--json` returns for it, on one line.
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Wallet
2026-01-01 open Expenses:Fees
2026-01-05 * "Exchange" "Withdrawal fee"
  fee-rate: 0.00000001
  quantity: 2.50
  settled: 2026-01-07
  cleared: TRUE
  fee-paid: 0.00000050 BTC
  memo: "ok"
  Expenses:Fees   0.00000050 BTC
    lot-size: 3
  Assets:Wallet  -0.00000050 BTC
"""
ENTRY_META = {
    "fee-rate": "0.00000001",
    "quantity": "2.50",
    "settled": "2026-01-07",
    "cleared": True,
    "fee-paid": {"number": "0.00000050", "currency": "BTC"},
    "memo": "ok",
}
QUERY = "SELECT meta, entry.meta AS entry_meta WHERE account = 'Expenses:Fees'"
REPR_MARKS = ("Decimal(", "datetime.", "1E-8", "True", "'")


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def _query(tmp_path: Path, ledger: Path, query: str, *args: str, json_mode: bool = False) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        HOME=str(tmp_path / "home"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
    )
    command = [sys.executable, "-m", "cli.main", *(["--json"] if json_mode else []), "--file", str(ledger)]
    done = subprocess.run(
        [*command, "query", *args, query],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def _json_row(tmp_path: Path, ledger: Path, query: str) -> list[object]:
    (row,) = json.loads(_query(tmp_path, ledger, query, json_mode=True))["data"]["rows"]
    assert isinstance(row, list)
    return row


def test_a_csv_metadata_cell_parses_as_the_json_cell(tmp_path: Path, ledger: Path) -> None:
    out = _query(tmp_path, ledger, QUERY, "-f", "csv")
    header, row = csv.reader(io.StringIO(out))

    assert header == ["meta", "entry_meta"]
    for mark in REPR_MARKS:
        assert mark not in out
    assert [json.loads(cell) for cell in row] == [{"lot-size": "3"}, ENTRY_META]
    assert [json.loads(cell) for cell in row] == _json_row(tmp_path, ledger, QUERY)


def test_a_csv_export_file_holds_the_same_cell(tmp_path: Path, ledger: Path) -> None:
    export = tmp_path / "out.csv"
    _query(tmp_path, ledger, QUERY, "-f", "csv", "-o", str(export))
    _, row = csv.reader(io.StringIO(export.read_text(encoding="utf-8")))

    assert [json.loads(cell) for cell in row] == [{"lot-size": "3"}, ENTRY_META]


def test_the_text_table_shows_the_same_cell(tmp_path: Path, ledger: Path) -> None:
    out = _query(tmp_path, ledger, "SELECT entry.meta AS entry_meta WHERE account = 'Expenses:Fees'", "-f", "text")
    (cell,) = [line.strip() for line in out.splitlines()[2:] if line.strip()]

    for mark in REPR_MARKS:
        assert mark not in cell
    assert json.loads(cell) == ENTRY_META


def test_the_entries_table_metadata_column_is_json_too(tmp_path: Path, ledger: Path) -> None:
    query = "SELECT meta FROM #entries WHERE type = 'transaction'"
    _, (cell,) = csv.reader(io.StringIO(_query(tmp_path, ledger, query, "-f", "csv")))

    assert json.loads(cell) == ENTRY_META


def test_scalar_metadata_lookups_are_unchanged(tmp_path: Path, ledger: Path) -> None:
    query = (
        "SELECT entry_meta('fee-rate'), entry_meta('settled'), entry_meta('cleared'), meta('lot-size') "
        "WHERE account = 'Expenses:Fees'"
    )
    _, row = csv.reader(io.StringIO(_query(tmp_path, ledger, query, "-f", "csv")))

    assert row == ["0.00000001", "2026-01-07", "TRUE", "3"]
