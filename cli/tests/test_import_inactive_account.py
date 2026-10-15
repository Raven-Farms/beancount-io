"""An import row posting to an account inactive on its date is blocked, not ready (w5/339).

Only "does an `open` exist" was asked, so a rule account closed before the
row, or opened after it, previewed the row as ready, and `--apply` then failed
ledger validation with exit 1, writing none of the valid rows either.
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
HEADER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Groceries USD
2026-01-01 open Expenses:Uncategorized USD
2026-01-01 open Equity:Opening
"""
DINING = {
    "closed": "2026-01-01 open Expenses:Dining USD\n2026-01-03 close Expenses:Dining\n",
    "late-open": "2026-02-01 open Expenses:Dining USD\n",
    "never-opened": "",
}
EXPECTED = {
    "closed": "Account 'Expenses:Dining' was closed 2026-01-03 (at ",
    "late-open": "Account 'Expenses:Dining' opens 2026-02-01 (at ",
    "never-opened": "Account 'Expenses:Dining' is not open.",
}


def _import(books: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    mapping = ["--csv", "date=Date,payee=Payee,narration=Narration,amount=Amount", "--account", "Assets:Checking"]
    return subprocess.run(
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
            "--rules",
            "r.toml",
            *flags,
        ],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _payload(result: subprocess.CompletedProcess[str]) -> Any:
    return json.loads(result.stdout or result.stderr)


@pytest.mark.parametrize("case", sorted(DINING))
def test_the_row_is_blocked_and_apply_exits_4(tmp_path: Path, case: str) -> None:
    ledger = HEADER + DINING[case]
    (tmp_path / "main.bean").write_text(ledger)
    (tmp_path / "s.csv").write_text(
        "Date,Payee,Narration,Amount\n2026-01-05,Whole Foods,lunch at cafe,-20.00\n2026-01-06,Joe Diner,dinner,-10.00\n"
    )
    (tmp_path / "r.toml").write_text('[[rule]]\nmatch = "diner"\naccount = "Expenses:Dining"\n')

    preview = _import(tmp_path)
    assert preview.returncode == 0, preview.stderr
    data = _payload(preview)["data"]
    assert data["ready"] == 1 and data["blocked"] == 1
    assert data["rows"][1]["status"] == "blocked"
    assert EXPECTED[case] in data["rows"][1]["reason"]

    applied = _import(tmp_path, "--apply")
    assert applied.returncode == 4, applied.stdout + applied.stderr
    assert (tmp_path / "main.bean").read_text() == ledger
