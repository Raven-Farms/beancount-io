"""A bank reference reused a month later is reviewed, not skipped, across exports (w5/599).

w5/075 made a reference repeated on another date a possible duplicate within
one export only. A monthly autopay arrives one month per file, so February's
rent matched January's entry as an exact duplicate and was dropped with exit
0. A ledger entry under the same id dated a week or more away is now a
possible duplicate. A date corrected in the ledger by days still matches.
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
LEDGER = """option "operating_currency" "USD"

2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Uncategorized
2026-01-01 open Equity:Opening

2026-01-02 * "Opening balance"
  Assets:Checking  1000.00 USD
  Equity:Opening
"""
HEADER = "Date,Description,Amount,Reference Number\n"


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "jan.csv").write_text(HEADER + "2026-01-01,Rent January,-1200.00,RENT-AUTOPAY\n")
    (tmp_path / "feb.csv").write_text(HEADER + "2026-02-01,Rent February,-1200.00,RENT-AUTOPAY\n")
    return tmp_path


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--no-input", "--file", str(books / "main.bean"), *args],
        cwd=books,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def _import(books: Path, name: str, *flags: str) -> tuple[int, list[dict[str, Any]]]:
    result = _bea(books, "import", name, "--account", "Assets:Checking", "--apply", *flags)
    payload = json.loads(result.stdout or result.stderr)
    data = payload["data"] if "data" in payload else payload["error"]["result"]
    return result.returncode, list(data["rows"])


def _checking(books: Path) -> str:
    result = _bea(books, "query", "SELECT sum(number) WHERE account = 'Assets:Checking'")
    assert result.returncode == 0, result.stderr
    return str(json.loads(result.stdout)["data"]["rows"][0][0])


def test_next_months_autopay_is_a_possible_duplicate(books: Path) -> None:
    assert _import(books, "jan.csv")[0] == 0
    before = (books / "main.bean").read_bytes()

    code, (row,) = _import(books, "feb.csv")

    assert code == 4
    assert row["status"] == "possible_duplicate"
    assert "Stable ID bank:RENT-AUTOPAY is already in the ledger on 2026-01-01, 31 days from this row" in row["reason"]
    assert (books / "main.bean").read_bytes() == before

    code, (row,) = _import(books, "feb.csv", "--duplicates", "include")
    assert code == 0 and row["status"] == "possible_duplicate"
    assert _checking(books) == "-1400.00"


def test_each_month_re_imported_is_its_own_exact_duplicate(books: Path) -> None:
    assert _import(books, "jan.csv")[0] == 0
    assert _import(books, "feb.csv", "--duplicates", "include")[0] == 0

    for name in ("jan.csv", "feb.csv"):
        code, (row,) = _import(books, name)
        assert code == 0, name
        assert row["status"] == "duplicate", (name, row["reason"])

    assert _checking(books) == "-1400.00"


def test_a_date_corrected_by_days_still_matches(books: Path) -> None:
    assert _import(books, "jan.csv")[0] == 0
    ledger = books / "main.bean"
    text = ledger.read_text()
    assert text.count('2026-01-01 ! "Rent January"') == 1, text
    ledger.write_text(text.replace('2026-01-01 ! "Rent January"', '2026-01-05 ! "Rent January"'))

    code, (row,) = _import(books, "jan.csv")

    assert code == 0
    assert row["status"] == "duplicate"
