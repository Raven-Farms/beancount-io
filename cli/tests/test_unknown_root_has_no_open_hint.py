"""An unknown account under a root the ledger lacks gets no `add open` remedy (w5/154).

The refusal for a posting to an unopened account ended with "To create it,
use bea add open --account …" whatever the account's root. Under a root the
ledger does not use, that command can only fail with `Invalid account name`,
so the message names the ledger's roots instead, as `bea import` does.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

RENAMED = """\
option "operating_currency" "EUR"
option "name_assets" "Aktiva"
option "name_expenses" "Aufwand"
2024-01-01 open Aktiva:Bank EUR
2024-01-01 open Aufwand:Essen EUR
2024-01-01 open Equity:Anfang EUR
2024-01-02 * "Opening"
  Aktiva:Bank  1000.00 EUR
  Equity:Anfang
"""
DEFAULT = """\
2024-01-01 open Assets:Bank EUR
2024-01-01 open Expenses:Food EUR
"""
OPEN_HINT = "bea add open"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _refused(tmp_path: Path, ledger: str, *args: str) -> str:
    """Run a write that must be refused untouched; return its output on one line."""
    main = tmp_path / "main.bean"
    main.write_text(ledger, encoding="utf-8")
    result = _bea(tmp_path, *args)
    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode == 1, output
    assert main.read_text(encoding="utf-8") == ledger
    return output


@pytest.mark.parametrize(
    ("ledger", "account", "contra", "roots"),
    [
        (RENAMED, "Expenses:Essen", "Aktiva:Bank", "Aktiva, Liabilities, Equity, Income, Aufwand"),
        (DEFAULT, "Foo:Bar", "Assets:Bank", "Assets, Liabilities, Equity, Income, Expenses"),
    ],
    ids=["renamed-roots", "default-roots"],
)
def test_foreign_root_names_the_roots_instead_of_add_open(
    tmp_path: Path, ledger: str, account: str, contra: str, roots: str
) -> None:
    output = _refused(
        tmp_path, ledger, "add", "transaction", "--date", "2024-03-02", "Brot", "-p", f"{account} 3 EUR", "-p", contra
    )

    assert f"unknown account '{account}'" in output
    assert f"its roots are {roots}" in output
    assert OPEN_HINT not in output


def test_foreign_root_on_a_balance_assertion_has_no_add_open_for_it(tmp_path: Path) -> None:
    output = _refused(
        tmp_path, RENAMED, "add", "balance", "--date", "2024-03-02", "--account", "Expenses:Essen", "--amount", "3 EUR"
    )

    assert "its roots are Aktiva, Liabilities, Equity, Income, Aufwand" in output
    assert f"{OPEN_HINT} --account" not in output


def test_account_under_a_ledger_root_keeps_a_working_add_open_hint(tmp_path: Path) -> None:
    output = _refused(
        tmp_path,
        RENAMED,
        *("add", "transaction", "--date", "2024-03-02", "Brot", "-p", "Aufwand:Neu 3 EUR", "-p", "Aktiva:Bank"),
    )

    assert "To create it, use bea add open --account Aufwand:Neu --date YYYY-MM-DD." in output
    assert "its roots are" not in output

    opened = _bea(tmp_path, "add", "open", "--account", "Aufwand:Neu", "--date", "2024-03-01")
    assert opened.returncode == 0, opened.stderr
    assert "open Aufwand:Neu" in (tmp_path / "main.bean").read_text(encoding="utf-8")
