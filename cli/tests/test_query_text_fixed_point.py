"""The `query --file` text table spells numbers and directives as a ledger would (w5/294).

Upstream's text renderers printed a sub-micro `Decimal` as `1E-8` (number
columns, `-m` sums, an `entry_meta()` cell) and a directive cell as its Python
repr, `Decimal('1E-8')` and `datetime.date(...)` included, while the position
beside it, the CSV and the JSON said `0.00000001`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """2026-01-01 open Assets:Wallet
2026-01-01 open Equity:Opening
2026-01-02 * "Dust"
  fee: 0.00000001
  Assets:Wallet  0.00000001 BTC
  Equity:Opening
"""
REPRS = ("1E-8", "Decimal(", "datetime.", "Transaction(", "Open(")


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    return tmp_path


def _query(books: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        XDG_DATA_HOME=str(books / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "query", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _assert_no_reprs(text: str) -> None:
    for needle in REPRS:
        assert needle not in text, text


def test_decimal_and_object_cells_are_fixed_point(books: Path) -> None:
    out = _query(books, "SELECT number, entry_meta('fee'), position WHERE account = 'Assets:Wallet'")
    _assert_no_reprs(out)
    assert out.splitlines()[-1].split() == ["0.00000001", "0.00000001", "0.00000001", "BTC"]


def test_numberify_sums_are_fixed_point_and_aligned(books: Path) -> None:
    out = _query(books, "-m", "SELECT account, sum(position) GROUP BY account")
    _assert_no_reprs(out)
    assert "Assets:Wallet    0.00000001" in out
    assert "Equity:Opening  -0.00000001" in out


def test_a_directive_cell_is_beancount_text(books: Path) -> None:
    out = _query(books, "SELECT date, entry WHERE account = 'Assets:Wallet'")
    _assert_no_reprs(out)
    assert '2026-01-02  2026-01-02 * "Dust"' in out
    assert "fee: 0.00000001" in out


def test_an_accounts_open_cell_and_a_text_export(books: Path) -> None:
    export = books / "out.txt"
    stdout = _query(books, "-o", str(export), "SELECT account, open FROM #accounts WHERE account = 'Assets:Wallet'")
    out = export.read_text() or stdout
    _assert_no_reprs(out)
    assert "2026-01-01 open Assets:Wallet" in out
