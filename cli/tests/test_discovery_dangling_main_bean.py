"""A dangling or non-file `main.bean` is not "absent" for cwd discovery (w5/295).

Discovery picked the default with `is_file()`, so a broken `main.bean` link
(an unmounted synced folder) or a `main.bean` directory fell through to an
older `main.beancount`: `check` passed and `add` wrote there, exit 0, while
`init` refused the same entry as an existing ledger.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening
"""
ADD = ("add", "open", "--account", "Assets:Savings", "--date", "2026-02-01", "-c", "USD")


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books.parent / "config"),
        XDG_CACHE_HOME=str(books.parent / "cache"),
        XDG_DATA_HOME=str(books.parent / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    books = tmp_path / "books"
    books.mkdir()
    (tmp_path / "sync").mkdir()
    (books / "main.beancount").write_text(LEDGER)
    return books


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("command", [("check",), ADD])
def test_a_dangling_main_bean_is_refused_not_bypassed(books: Path, command: tuple[str, ...]) -> None:
    (books / "main.bean").symlink_to("../sync/ledger.bean")
    before = _digest(books / "main.beancount")
    result = _bea(books, *command)
    assert result.returncode == 2, result.stdout + result.stderr
    message = " ".join(result.stderr.split())
    assert "main.bean' (from the working directory) is a broken symbolic link to '../sync/ledger.bean'" in message
    assert _digest(books / "main.beancount") == before


def test_a_main_bean_directory_is_refused_not_bypassed(books: Path) -> None:
    (books / "main.bean").mkdir()
    before = _digest(books / "main.beancount")
    result = _bea(books, *ADD)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "is a directory" in result.stderr
    assert _digest(books / "main.beancount") == before


def test_without_main_bean_the_fallback_still_serves(books: Path) -> None:
    result = _bea(books, *ADD)
    assert result.returncode == 0, result.stderr
    assert "Assets:Savings" in (books / "main.beancount").read_text()
