"""A forecast plugin's projections are not existing entries for import (w5/325).

Import matched rows against every loaded transaction, so each real payment a
`fava.plugins.forecast` template projected became a possible duplicate cited
at the template's line, and `--duplicates skip` wrote none of them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
plugin "fava.plugins.forecast"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Rent USD
2026-01-01 open Expenses:Uncategorized USD
2026-01-01 open Equity:Opening
2026-01-02 * "Open"
  Assets:Checking  5000.00 USD
  Equity:Opening
2026-01-05 # "Landlord" "Rent [MONTHLY UNTIL 2026-04-01]"
  Expenses:Rent  1000.00 USD
  Assets:Checking
"""
PAID = """2026-02-05 * "Landlord" "Rent"
  Expenses:Rent  1000.00 USD
  Assets:Checking
"""
CSV = "Date,Payee,Amount\n2026-02-05,Landlord,-1000.00\n2026-03-05,Landlord,-1000.00\n"


def _import(books: Path, *flags: str) -> Any:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    mapping = ["--csv", "date=Date,payee=Payee,amount=Amount", "--account", "Assets:Checking"]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "--json",
            "--no-input",
            "-f",
            "main.bean",
            "import",
            "s.csv",
            *mapping,
            *flags,
        ],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["data"]


def _books(tmp_path: Path, ledger: str) -> Path:
    (tmp_path / "main.bean").write_text(ledger)
    (tmp_path / "s.csv").write_text(CSV)
    return tmp_path


def test_projected_rows_are_new_and_skip_writes_them(tmp_path: Path) -> None:
    books = _books(tmp_path, LEDGER)
    preview = _import(books)
    assert [row["status"] for row in preview["rows"]] == ["new", "new"]

    applied = _import(books, "--apply", "--duplicates", "skip")
    assert applied["written"] == 2
    text = (books / "main.bean").read_text()
    assert "2026-02-05" in text and "2026-03-05" in text


def test_a_written_payment_is_still_a_duplicate(tmp_path: Path) -> None:
    books = _books(tmp_path, LEDGER + PAID)
    rows = _import(books)["rows"]
    assert [row["status"] for row in rows] == ["possible_duplicate", "new"]
    assert rows[0]["match"]["lineno"] == LEDGER.count("\n") + 1
