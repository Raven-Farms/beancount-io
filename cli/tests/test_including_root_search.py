"""A leaf deep below its root, or beside it through `../`, is still found (w5/347).

`including_root` looked only in the leaf's directory and its parent, and
compared resolved paths: a leaf three directories down, a `../shared` include
and a case-variant path on macOS went unfound, so a write to them was checked
against the leaf alone. A `.bean` FIFO nearby must not stall the wider search.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
include "years/2026/q1/jan.bean"
include "../shared/common.bean"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
"""


@pytest.fixture
def books(tmp_path: Path) -> Path:
    books = tmp_path / "x" / "books"
    (books / "years" / "2026" / "q1").mkdir(parents=True)
    (tmp_path / "x" / "shared").mkdir()
    (books / "main.bean").write_text(MAIN)
    (books / "years" / "2026" / "q1" / "jan.bean").write_text("; january\n")
    (tmp_path / "x" / "shared" / "common.bean").write_text("; shared\n")
    (tmp_path / "elsewhere").mkdir()
    return books


def _add(books: Path, leaf: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books.parent.parent / "config"),
        XDG_CACHE_HOME=str(books.parent.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    args = ["add", "transaction", "T", "--date", "2026-01-05", "-p", "Expenses:Food 2 USD", "-p", "Assets:Cash"]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "-f", str(leaf), *args],
        env=env,
        cwd=books.parent.parent / "elsewhere",
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("leaf", ["years/2026/q1/jan.bean", "../shared/common.bean"], ids=["three-down", "sibling"])
def test_the_root_is_found_and_the_write_lands_in_the_leaf(books: Path, leaf: str) -> None:
    path = (books / leaf).resolve()
    result = _add(books, path)
    assert result.returncode == 0, result.stderr
    assert f"is included by {books / 'main.bean'}" in " ".join(result.stderr.split())
    assert '2026-01-05 * "T"' in path.read_text()


@pytest.mark.skipif(sys.platform != "darwin", reason="case-insensitive volume")
def test_a_case_variant_path_is_found_and_named(books: Path) -> None:
    variant = Path(
        str(books / "years" / "2026" / "q1" / "jan.bean").replace("years/2026/q1/jan.bean", "YEARS/2026/Q1/JAN.BEAN")
    )
    result = _add(books, variant)
    assert result.returncode != 0
    assert "Pass --into years/2026/q1/jan.bean" in " ".join(result.stderr.split())


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX FIFO")
def test_a_fifo_nearby_does_not_stall_the_search(books: Path) -> None:
    os.mkfifo(books.parent / "pipe.bean")
    result = _add(books, books / "years" / "2026" / "q1" / "jan.bean")
    assert result.returncode == 0, result.stderr
