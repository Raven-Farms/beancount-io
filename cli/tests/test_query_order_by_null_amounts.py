"""`ORDER BY` an Amount column holding NULLs sorts them first, in any posting order (w5/562).

Beanquery's NULL compares smaller than anything only when asked itself, and
Beancount's `Amount.__lt__` runs first and reads `.currency` off it: `SELECT
account, price ORDER BY price` exited 1 as a ledger "validation" failure with
`AttributeError: 'NullType' object has no attribute 'currency'` whenever an
unpriced posting sorted against a priced one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPENS = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Assets:Eur EUR\n"
CASH = "  Assets:Cash  -11.00 USD\n"
EURO = "  Assets:Eur  10.00 EUR @ 1.10 USD\n"
ORDERS = {"unpriced-first": CASH + EURO, "priced-first": EURO + CASH}


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize("postings", ORDERS.values(), ids=ORDERS.keys())
@pytest.mark.parametrize(("direction", "first"), [("", "Assets:Cash"), (" DESC", "Assets:Eur")])
def test_nulls_sort_first_whatever_the_posting_order(tmp_path: Path, postings: str, direction: str, first: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(OPENS + '2026-01-02 * "FX"\n' + postings)
    query = f"SELECT account, price ORDER BY price{direction}"

    result = _bea(tmp_path, "--json", "--file", str(ledger), "query", query)
    native = _bea(tmp_path, "query", "--source", str(ledger), query)

    assert result.returncode == 0, result.stderr
    rows = json.loads(result.stdout)["data"]["rows"]
    assert [row[0] for row in rows][0] == first, rows
    assert {row[0]: row[1] for row in rows}["Assets:Cash"] is None
    assert native.returncode == 0, native.stderr
    assert "NullType" not in native.stdout + native.stderr
