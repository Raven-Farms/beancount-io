"""An import row's source amount is spelled in fixed-point notation (w5/228).

The preview table's SOURCE AMOUNT column and the JSON row's `amount` field
interpolated the number with `str(Decimal)`, which switches to scientific
notation below one millionth: a `-0.00000050 BTC` row read `-5.0E-7 BTC`
beside a diff that spelled it out, a value `bea` refuses as input.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "BTC"
2026-01-01 open Assets:Wallet BTC
2026-01-01 open Expenses:Uncategorized
"""
EXPORT = """\
Date,Description,Amount
2026-02-01,Network fee,-0.00000050
2026-02-02,Dust sweep,0.00000546
"""
IMPORT = ("import", "w.csv", "--csv", "date=Date,narration=Description,amount=Amount", "--account", "Assets:Wallet")


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "w.csv").write_text(EXPORT)
    return tmp_path


def _bea(books: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _rows(books: Path, *extra: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = json.loads(_bea(books, "--json", "-f", "main.bean", *IMPORT, *extra))["data"]["rows"]
    return rows


def test_preview_table_spells_a_tiny_amount_in_fixed_point(books: Path) -> None:
    table = [line.split() for line in _bea(books, "-f", "main.bean", *IMPORT).splitlines()]
    amounts = {line[0]: " ".join(line[5:7]) for line in table if line and line[0] in {"1", "2"}}

    # Row 2 is the control: seven places down it was already written out.
    assert amounts == {"1": "-0.00000050 BTC", "2": "0.00000546 BTC"}


@pytest.mark.parametrize("extra", [(), ("--apply",)], ids=["preview", "apply"])
def test_json_row_amount_is_fixed_point_and_agrees_with_the_entry(books: Path, extra: tuple[str, ...]) -> None:
    fee, dust = _rows(books, *extra)

    assert fee["amount"] == "-0.00000050 BTC"
    assert dust["amount"] == "0.00000546 BTC"
    # The row's own entry text was always right; the field now says the same.
    assert f"Assets:Wallet           {fee['amount']}" in fee["entry"]
    assert "E" not in fee["amount"].split()[0]
