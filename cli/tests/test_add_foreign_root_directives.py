"""`add open`, `close`, `custom` name a root the ledger does not use (w5/402).

w5/154's root message reached postings and references only; these ended at
Beancount's bare "Invalid account name: Expenses:X".
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
option "name_assets" "Aktiva"
option "name_liabilities" "Passiva"
option "name_equity" "Eigenkapital"
option "name_income" "Ertrag"
option "name_expenses" "Aufwand"
2026-01-01 open Aktiva:Bank USD
2026-01-01 open Aufwand:Essen USD
"""
MESSAGE = (
    "Account '{account}' has root 'Expenses', which this ledger does not use; its roots are Aktiva, Passiva, "
    "Eigenkapital, Ertrag, Aufwand (set by the name_* options). Use one of those roots."
)


def _add(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "add", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("args", "account"),
    [
        (["open", "--account", "Expenses:X", "--date", "2026-01-01"], "Expenses:X"),
        (["close", "--account", "Expenses:Essen", "--date", "2026-02-01"], "Expenses:Essen"),
        (["custom", "--date", "2026-01-05", "--type", "budget", "--value", "account:Expenses:Essen"], "Expenses:Essen"),
    ],
    ids=["open", "close", "custom"],
)
def test_a_foreign_root_is_refused_with_the_root_message(tmp_path: Path, args: list[str], account: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _add(tmp_path, *args)
    assert result.returncode == 2, result.stderr
    assert MESSAGE.format(account=account) in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_a_renamed_root_open_still_writes(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _add(tmp_path, "open", "--account", "Aufwand:Neu", "--date", "2026-01-01")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "main.bean").read_text().endswith("2026-01-01 open Aufwand:Neu\n")
