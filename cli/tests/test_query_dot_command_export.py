"""A one-shot dot command's `-o` export holds what it printed, or is left alone (w5/289).

On `--source`, `.help` and `.parse` wrote to process stdout instead of the
output buffer, and the empty buffer then replaced an existing export with a
zero-byte file under exit 0. Commands that print nothing did the same on both
paths.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Equity:Opening USD
2024-01-02 * "Open"
  Assets:Cash  100.00 USD
  Equity:Opening
"""
BROKEN = """\
2024-01-01 open Assets:Cash USD
2024-01-02 * "Open"
  Assets:Cash  100.00 USD
  Equity:Nope
"""
KEPT = "MARKER old export\n"
FILE = ["--file", "main.bean", "query"]
SOURCE = ["query", "--source", "main.bean"]
SURFACES = pytest.mark.parametrize("surface", [FILE, SOURCE], ids=["file", "source"])


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    (tmp_path / "out.txt").write_text(KEPT, encoding="utf-8")
    return tmp_path


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        HOME=str(books / "home"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        stdin=subprocess.DEVNULL,
        cwd=books,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _exported(books: Path) -> str:
    return (books / "out.txt").read_text(encoding="utf-8")


@SURFACES
@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (".help", "Shell utility commands"),
        (".parse SELECT 1", "(select"),
        # Controls: these already reached the buffer on both paths.
        (".tables", "postings"),
        (".errors", "(no errors)"),
    ],
)
def test_a_dot_command_exports_what_it_prints(books: Path, surface: list[str], command: str, expected: str) -> None:
    result = _bea(books, *surface, "-o", "out.txt", command)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""
    assert expected in _exported(books)
    assert KEPT not in _exported(books)


@pytest.mark.parametrize("command", [".help", ".parse SELECT 1"])
def test_source_help_and_parse_still_print_without_an_export(books: Path, command: str) -> None:
    result = _bea(books, *SOURCE, command)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
    assert _exported(books) == KEPT


@SURFACES
@pytest.mark.parametrize("command", [".history", ".reload", ".run", ".clear"])
def test_a_dot_command_that_prints_nothing_leaves_the_export(books: Path, surface: list[str], command: str) -> None:
    result = _bea(books, *surface, "-o", "out.txt", command)

    assert result.returncode == 0, result.stderr
    assert "Nothing was written to" in result.stderr
    assert "out.txt" in result.stderr
    assert _exported(books) == KEPT

    # Nor is a zero-byte file created where there was none.
    fresh = _bea(books, *surface, "-o", "new.txt", command)
    assert fresh.returncode == 0, fresh.stderr
    assert not (books / "new.txt").exists()


@pytest.mark.parametrize(
    "surface",
    [["--file", "main.bean", "query", "--allow-errors"], SOURCE],
    ids=["file", "source"],
)
def test_errors_printed_elsewhere_do_not_empty_the_export(books: Path, surface: list[str]) -> None:
    (books / "main.bean").write_text(BROKEN, encoding="utf-8")

    result = _bea(books, *surface, "-o", "out.txt", ".errors")

    assert result.returncode == 0, result.stderr
    assert "Equity:Nope" in result.stdout + result.stderr
    assert "Nothing was written to" in result.stderr
    assert _exported(books) == KEPT


@SURFACES
def test_a_query_with_no_rows_still_replaces_the_export(books: Path, surface: list[str]) -> None:
    result = _bea(books, *surface, "-o", "out.txt", "PRINT FROM year = 1999")

    assert result.returncode == 0, result.stderr
    assert "Nothing was written" not in result.stderr
    assert _exported(books) == ""
