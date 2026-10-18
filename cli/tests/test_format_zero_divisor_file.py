"""One file with a zero divisor no longer aborts `bea format` for the rest (w5/565).

The pre-format syntax pass parsed every file in one engine process, and
Beancount's parser segfaults on `100/0`: the batch died naming no file, and
nothing was formatted. Each file is now scanned first, and that one alone is
reported as cannot-parse.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = (
    'option "operating_currency" "USD"\n2020-01-01 open Assets:Cash USD\n2020-01-01 open Income:Gains\n'
    'include "jan.bean"\ninclude "feb.bean"\n'
)
# A slash date, and `/0` in a string and a comment, are no divisors.
JAN = '2020/01/05 * "a" "ratio 3/0"\n    Assets:Cash     1 USD ; was 1/0\n  Income:Gains   -1 USD\n'
FEB = '2020-02-01 * "b"\n  Assets:Cash  100/0 USD\n  Income:Gains\n'


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    books = tmp_path / "books"
    books.mkdir()
    for name, text in (("main.bean", MAIN), ("jan.bean", JAN), ("feb.bean", FEB)):
        (books / name).write_text(text)
    return books


def _named(books: Path, output: str) -> None:
    assert f"{books / 'feb.bean'}:2: Division by zero in an amount expression" in output, output
    assert "SIGSEGV" not in output and "jan.bean:" not in output


@pytest.mark.parametrize("target", ["books", "books/main.bean"], ids=["directory", "root"])
def test_in_place_formats_the_others_and_names_the_file(tmp_path: Path, books: Path, target: str) -> None:
    result = _bea(tmp_path, "format", "-i", target)

    assert result.returncode == 1, result.stdout + result.stderr
    _named(books, result.stdout + result.stderr)
    assert (
        books / "jan.bean"
    ).read_text() == '2020/01/05 * "a" "ratio 3/0"\n  Assets:Cash    1 USD ; was 1/0\n  Income:Gains  -1 USD\n'
    assert (books / "feb.bean").read_text() == FEB


def test_check_names_the_file_beside_the_one_to_format(tmp_path: Path, books: Path) -> None:
    result = _bea(tmp_path, "format", "--check", "books")

    assert result.returncode == 1, result.stdout + result.stderr
    _named(books, result.stdout + result.stderr)
    lines = (result.stdout + result.stderr).splitlines()
    assert any(line.lower() == f"would format: {books / 'jan.bean'}".lower() for line in lines), lines
    assert (books / "jan.bean").read_text() == JAN
