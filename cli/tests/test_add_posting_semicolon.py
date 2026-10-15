"""A `;` in posting text is refused, not dropped as a comment (w5/298).

Beancount's grammar ends a posting at `;`, so `-p 'Expenses:Food 12.50 USD ;
split'` lost the note, `-p 'Expenses:Food ; 8.00 USD'` became the inferred
leg, and a price or cost after the `;` vanished, each with exit 0. A bulk
row's `amount` lost its trailing comment the same way.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Equity:Opening USD
2026-01-01 open Assets:Brk
2026-01-01 open Assets:Cash
2026-01-02 * "Open"
  Assets:Checking  100.00 USD
  Equity:Opening
"""


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    return path


def _bea(ledger: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(ledger.parent / "config"),
        XDG_CACHE_HOME=str(ledger.parent / "cache"),
        XDG_DATA_HOME=str(ledger.parent / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "-f", str(ledger), *args],
        env=env,
        cwd=ledger.parent,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    "postings",
    [
        ("Expenses:Food 12.50 USD ; split with Sam", "Assets:Checking"),
        ("Expenses:Food ; 8.00 USD", "Assets:Checking -8.00 USD"),
        ("Assets:Brk 1 AAPL {100 USD} ; @ 200 USD", "Assets:Cash"),
        ("Assets:Brk 1 AAPL ; {100 USD}", "Assets:Cash"),
    ],
)
def test_a_semicolon_in_a_posting_is_refused(ledger: Path, postings: tuple[str, str]) -> None:
    args = [arg for posting in postings for arg in ("-p", posting)]
    result = _bea(ledger, "add", "transaction", "X", "--date", "2026-01-05", *args)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "--posting 1 contains a ';'" in " ".join(result.stderr.split())
    assert ledger.read_text() == LEDGER


def test_a_semicolon_in_a_bulk_amount_is_refused(ledger: Path) -> None:
    rows = ledger.parent / "rows.json"
    row = {
        "date": "2026-01-05",
        "narration": "Lunch",
        "postings": [{"account": "Expenses:Food", "amount": "12.50 USD ; split"}, {"account": "Assets:Checking"}],
    }
    rows.write_text(json.dumps([row]))
    result = _bea(ledger, "add", "transactions", "--from", str(rows))
    assert result.returncode != 0, result.stdout
    assert "contains a ';'" in " ".join(result.stderr.split())
    assert ledger.read_text() == LEDGER


def test_a_semicolon_inside_a_quoted_lot_label_is_kept(ledger: Path) -> None:
    result = _bea(
        ledger,
        "add",
        "transaction",
        "X",
        "--date",
        "2026-01-05",
        "-p",
        'Assets:Brk 1 AAPL {100 USD, "a;b"}',
        "-p",
        "Assets:Cash",
    )
    assert result.returncode == 0, result.stderr
    assert '"a;b"' in ledger.read_text()
