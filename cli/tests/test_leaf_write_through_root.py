"""A write with `--file` on an included leaf is checked against the root that includes it (w5/343).

Validated alone, the leaf saw every root account as unknown and told the user
to `add open` it again; following that wrote a duplicate `open`, exit 0, that
broke the whole ledger. The write now lands in the leaf, checked through the
root, as the `--into` recipe would.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
include "sub dir/extra.bean"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Equity:Opening
"""
LEAF = "2026-01-01 open Expenses:Rent USD\n2026-01-03 close Expenses:Rent\n"


@pytest.fixture
def books(tmp_path: Path) -> Path:
    books = tmp_path / "my books"
    (books / "sub dir").mkdir(parents=True)
    (books / "main.bean").write_text(MAIN)
    (books / "sub dir" / "extra.bean").write_text(LEAF)
    (tmp_path / "elsewhere").mkdir()
    return books


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books.parent / "config"),
        XDG_CACHE_HOME=str(books.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=books.parent / "elsewhere",
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_a_transaction_on_root_accounts_lands_in_the_leaf(books: Path) -> None:
    leaf = books / "sub dir" / "extra.bean"
    result = _bea(
        books,
        "-f",
        str(leaf),
        "add",
        "transaction",
        "X",
        "--date",
        "2026-01-02",
        "-p",
        "Expenses:Food 5 USD",
        "-p",
        "Assets:Cash",
    )
    assert result.returncode == 0, result.stderr
    assert "is included by" in result.stderr and "checked against that whole ledger" in result.stderr
    assert "To create it" not in result.stderr
    assert '2026-01-02 * "X"' in leaf.read_text()
    assert _bea(books, "-f", str(books / "main.bean"), "check").returncode == 0


def test_a_duplicate_open_in_the_leaf_is_refused(books: Path) -> None:
    leaf = books / "sub dir" / "extra.bean"
    result = _bea(books, "-f", str(leaf), "add", "open", "--account", "Assets:Cash", "--date", "2026-01-01")
    assert result.returncode == 1
    assert "Duplicate open directive for Assets:Cash" in result.stderr
    assert leaf.read_text() == LEAF
    assert _bea(books, "-f", str(books / "main.bean"), "check").returncode == 0


def test_a_never_opened_account_still_gets_the_add_open_remedy(books: Path) -> None:
    leaf = books / "sub dir" / "extra.bean"
    result = _bea(
        books,
        "-f",
        str(leaf),
        "add",
        "transaction",
        "Y",
        "--date",
        "2026-01-02",
        "-p",
        "Expenses:Nope 5 USD",
        "-p",
        "Assets:Cash",
    )
    assert result.returncode == 1
    assert "To create it, use bea add open --account Expenses:Nope" in " ".join(result.stderr.split())
    assert leaf.read_text() == LEAF
