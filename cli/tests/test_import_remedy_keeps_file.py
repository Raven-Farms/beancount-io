"""A printed remedy acts on the ledger it is about, wherever it is pasted (w5/303).

`bea --file books/main.bean import …` printed `Run: bea add open …` without the
`--file`: pasted from the same directory it was refused, or it opened the
account in a decoy `main.bean` there while the import stayed blocked. The
empty-BQL-window hint dropped the ledger the same way.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-08-01 open Assets:Checking USD
2026-08-01 open Expenses:Uncategorized
2026-08-01 open Equity:Opening
"""
IMPORT = [
    "import",
    "statement.csv",
    "--csv",
    "date=Date,amount=Amount,payee=Payee,narration=Narration",
    "--account",
    "Assets:Checking",
    "--rules",
    "rules.toml",
]


def _bea(work: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(work.parent / "config"),
        XDG_CACHE_HOME=str(work.parent / "cache"),
        XDG_DATA_HOME=str(work.parent / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=cwd or work,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def work(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    (work / "books").mkdir(parents=True)
    (work / "books" / "main.bean").write_text(LEDGER)
    (work / "statement.csv").write_text("Date,Payee,Narration,Amount\n2026-08-02,Whole Foods,groceries,-20.00\n")
    (work / "rules.toml").write_text('[[rule]]\nmatch = "whole foods"\naccount = "Expenses:Groceries"\n')
    return work


def _remedy(output: str) -> list[str]:
    found = re.search(r"Run: (bea .*?)\.\s*$", output, re.MULTILINE)
    assert found, output
    return shlex.split(found.group(1))


@pytest.mark.parametrize("decoy", [False, True], ids=["no-decoy", "decoy"])
def test_the_pasted_add_open_unblocks_the_imported_ledger(work: Path, decoy: bool) -> None:
    if decoy:
        (work / "main.bean").write_text(LEDGER)
    preview = _bea(work, "--file", "books/main.bean", *IMPORT)
    assert preview.returncode == 0, preview.stderr
    remedy = _remedy(preview.stdout + preview.stderr)
    assert remedy[:3] == ["bea", "--file", "books/main.bean"]

    pasted = _bea(work, *remedy[1:])
    assert pasted.returncode == 0, pasted.stderr
    assert "open Expenses:Groceries" in (work / "books" / "main.bean").read_text()
    if decoy:
        assert (work / "main.bean").read_text() == LEDGER
    again = _bea(work, "--file", "books/main.bean", *IMPORT)
    assert "blocked" not in again.stdout + again.stderr


def test_inside_the_ledger_directory_the_short_form_stays(work: Path) -> None:
    args = [arg.replace("statement.csv", "../statement.csv").replace("rules.toml", "../rules.toml") for arg in IMPORT]
    preview = _bea(work, *args, cwd=work / "books")
    assert _remedy(preview.stdout + preview.stderr)[:3] == ["bea", "add", "open"]


def test_the_empty_window_hint_names_the_ledger(work: Path) -> None:
    result = _bea(work, "--file", "books/main.bean", "query", "SELECT date FROM OPEN ON 2026-08-02 CLOSE ON 2026-08-02")
    assert result.returncode == 2
    assert "Or run: bea --file books/main.bean list transaction --from-date 2026-08-02" in result.stderr
