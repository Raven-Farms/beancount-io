"""An output or load cache under another case of a glob-included directory is refused (w5/595).

The include-claim checks (w5/072, w5/296, w5/497) compared resolved directory
strings, and on a case-insensitive volume `resolve()` keeps the spelling
typed. `-o Txns/backup.bean` for `include "txns/*.bean"` landed in `txns/`
and doubled every balance while `check` passed. A cache named `TXNS/…` wrote
a pickle the next load tried to read as ledger text.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Cash USD\n"
    "2026-01-01 open Equity:Opening USD\n"
    'include "{include}"\n'
)
TRANSACTION = '2026-01-02 * "a"\n  Assets:Cash  5 USD\n  Equity:Opening\n'


def _case_insensitive(directory: Path) -> bool:
    probe = directory / "case-probe"
    probe.mkdir()
    try:
        return (directory / "CASE-PROBE").exists()
    finally:
        probe.rmdir()


@pytest.fixture
def books(tmp_path: Path) -> Path:
    if not _case_insensitive(tmp_path):
        pytest.skip("the filesystem is case-sensitive, so Txns/ is another directory")
    books = tmp_path / "books"
    (books / "txns").mkdir(parents=True)
    (books / "main.bean").write_text(MAIN.format(include="txns/*.bean"))
    (books / "txns" / "a.bean").write_text(TRANSACTION)
    return books


def _bea(books: Path, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BEA_", "BEANCOUNT_")) and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books.parent / "config"),
        XDG_CACHE_HOME=str(books.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        **extra,
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), *args],
        cwd=books,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def _refused(result: subprocess.CompletedProcess[str], books: Path) -> str:
    assert result.returncode == 2, result.stdout + result.stderr
    assert sorted(path.name for path in (books / "txns").iterdir()) == ["a.bean"]
    return " ".join(result.stderr.split())


@pytest.mark.parametrize(
    "command",
    [
        ["query", "PRINT FROM date >= 2026-01-02", "-o", "Txns/backup.bean"],
        ["format", "main.bean", "-o", "Txns/f.bean"],
    ],
    ids=["query", "format"],
)
def test_an_output_under_another_case_of_the_directory_is_refused(books: Path, command: list[str]) -> None:
    message = _refused(_bea(books, *command), books)

    assert 'would become part of the ledger it reads: include "txns/*.bean"' in message


def test_a_cache_filename_under_another_case_is_refused(books: Path) -> None:
    message = _refused(_bea(books, "check", "--cache-filename", "TXNS/zcache.bean"), books)

    assert 'which include "txns/*.bean"' in message
    assert "would load as part of the ledger once the cache is written" in message


def test_a_cache_variable_under_another_case_is_refused(books: Path) -> None:
    message = _refused(_bea(books, "balance", BEANCOUNT_LOAD_CACHE_FILENAME="TXNS/envcache.bean"), books)

    assert "BEANCOUNT_LOAD_CACHE_FILENAME TXNS/envcache.bean" in message
    assert "would load as part of the ledger once the cache is written" in message


def test_a_new_directory_under_another_case_is_refused(books: Path) -> None:
    """The engine's check for a directory the export would create (w5/296)."""
    (books / "main.bean").write_text(MAIN.format(include="txns/*/*.bean"))

    message = _refused(_bea(books, "price", "export", "-o", "Txns/snap"), books)

    assert "Txns/snap/main.bean would become part of the ledger being exported" in message


def test_the_ledger_still_answers(books: Path) -> None:
    result = _bea(books, "query", "SELECT sum(position) WHERE account = 'Assets:Cash'")

    assert result.returncode == 0, result.stderr
    assert "5 USD" in result.stdout and "10 USD" not in result.stdout
