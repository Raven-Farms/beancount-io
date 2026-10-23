"""`price export` refuses an output directory an include glob would read back (w5/814).

The include guards checked every file the export plans, never the directory
it creates: `-o txns/p.bean` under `include "txns/*.bean"` exported, exit 0,
into a directory the glob then matched, and every later load failed with
"is a directory, not a file".
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening
include "txns/*.bean"
"""
TXN = '2026-01-02 * "Open"\n  Assets:Cash  100.00 USD\n  Equity:Opening\n'


@pytest.fixture
def books(tmp_path: Path) -> Path:
    books = tmp_path / "books"
    (books / "txns").mkdir(parents=True)
    (books / "main.bean").write_text(MAIN)
    (books / "txns" / "a.bean").write_text(TXN)
    return books


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
        [sys.executable, "-m", "cli.main", "--no-input", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("output", ["txns/p.bean", "Txns/p.bean"], ids=["as-listed", "other-case"])
def test_an_export_directory_the_glob_claims_is_refused(books: Path, output: str) -> None:
    if output != output.lower() and not (books / output.split("/", 1)[0]).exists():
        pytest.skip("case-sensitive volume: Txns/ is another directory")
    before = sorted(path.name for path in (books / "txns").iterdir())

    result = _bea(books, "price", "export", "-o", output)

    assert result.returncode == 2, result.stdout + result.stderr
    message = " ".join(result.stderr.split())
    assert f"Cannot export: the directory {output} would become part of the ledger being exported" in message
    assert "txns/*.bean" in message
    assert "Nothing was written" in message
    assert sorted(path.name for path in (books / "txns").iterdir()) == before
    assert _bea(books, "check").returncode == 0


def test_a_directory_outside_the_glob_still_exports(books: Path) -> None:
    result = _bea(books, "price", "export", "-o", "txns/p.snapshot")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (books / "txns" / "p.snapshot" / "main.bean").is_file()
    assert _bea(books, "check").returncode == 0
