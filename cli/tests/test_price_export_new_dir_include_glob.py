"""`price export` into a directory an include glob would read back is refused (w5/296).

The guard from w5/072 expanded each include pattern's directory part against
the disk as it was, so a destination directory the export was about to create
(`main-export/`, a new `-o snap`) was never listed: the export wrote a copy
of the books that `include "*/*.bean"` then loaded twice.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
2026-01-01 open Assets:Bank USD
2026-01-01 open Equity:Opening
include "{pattern}"
"""
MONTH = """2026-01-02 * "Open"
  Assets:Bank  100.00 USD
  Equity:Opening
"""


def _books(tmp_path: Path, pattern: str) -> Path:
    books = tmp_path / "books"
    (books / "2026").mkdir(parents=True)
    (books / "main.bean").write_text(MAIN.format(pattern=pattern))
    (books / "2026" / "01.bean").write_text(MONTH)
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


@pytest.mark.parametrize(
    ("pattern", "output", "created"),
    [
        ("*/*.bean", None, "main-export"),
        ("*/*.bean", "snap", "snap"),
        ("**/*.bean", "deep/er", "deep"),
    ],
)
def test_a_new_directory_the_include_glob_reaches_is_refused(
    tmp_path: Path, pattern: str, output: str | None, created: str
) -> None:
    books = _books(tmp_path, pattern)
    result = _bea(books, "price", "export", *(["-o", output] if output else []))
    assert result.returncode == 2, result.stdout + result.stderr
    assert "would become part of the ledger being exported" in " ".join(result.stderr.split())
    assert not (books / created).exists()
    if pattern == "*/*.bean":
        assert _bea(books, "check").returncode == 0


def test_a_new_directory_no_pattern_reaches_is_still_written(tmp_path: Path) -> None:
    books = _books(tmp_path, "*/*.bean")
    result = _bea(books, "price", "export", "-o", str(tmp_path / "outside"))
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "outside" / "main.bean").is_file()
    hidden = _bea(books, "price", "export", "-o", ".snap")
    assert hidden.returncode == 0, hidden.stderr
    assert _bea(books, "check").returncode == 0
