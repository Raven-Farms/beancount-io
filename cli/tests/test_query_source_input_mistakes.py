"""Input mistakes in a native `query --source` are one-line usage errors (w5/293).

w5/250 fixed the I/O cases and left four non-I/O triggers printing a boxed
Python traceback with exit 1: a `csv:` URI parameter the reader rejects, `-m` on
a `csv:` source (no display precision), `-f beancount` on a column result, and a
dot command with an unbalanced quote. `.describe 'x` also leaked
`ValueError: No closing quotation` on `--file`. Each now exits 2 in one line,
and a refused one-shot leaves an existing `-o` export as it was.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """2026-01-01 open Assets:Wallet
2026-01-01 open Equity:Opening
2026-01-02 * "Dust"
  Assets:Wallet  0.00000001 BTC
  Equity:Opening
"""
PREVIOUS = "keep\n"


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "t.csv").write_text("name,amount\nalpha,1.5\nbeta,2\n")
    (tmp_path / "out.txt").write_text(PREVIOUS)
    return tmp_path


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        XDG_DATA_HOME=str(books / "data"),
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


def _assert_one_line_usage(result: subprocess.CompletedProcess[str], needle: str) -> None:
    assert result.returncode == 2, result.stderr
    assert "Traceback" not in result.stderr
    assert needle in " ".join(result.stderr.split())


@pytest.mark.parametrize(
    ("params", "needle"),
    [
        ("header=true", "multiple values for keyword argument 'header'"),
        ("header=false", "multiple values for keyword argument 'header'"),
        ("encoding=bogus", "unknown encoding: bogus"),
        ("foo=bar", "'foo'"),
        ("dialect=nope", "unknown dialect"),
    ],
)
def test_a_bad_csv_parameter_is_a_usage_error(books: Path, params: str, needle: str) -> None:
    source = f"csv:{books / 't.csv'}?{params}"
    result = _bea(books, "query", "--source", source, "-o", str(books / "out.txt"), "SELECT * FROM t")
    _assert_one_line_usage(result, "Cannot open --source")
    assert needle in result.stderr
    assert (books / "out.txt").read_text() == PREVIOUS


def test_numberify_on_a_csv_source_is_refused(books: Path) -> None:
    result = _bea(books, "query", "--source", f"csv:{books / 't.csv'}", "-m", "SELECT * FROM t")
    _assert_one_line_usage(result, "--numberify (-m) needs a Beancount ledger source")


def test_beancount_format_on_a_column_result_is_refused_on_source(books: Path) -> None:
    result = _bea(books, "query", "--source", str(books / "main.bean"), "-f", "beancount", "SELECT account")
    _assert_one_line_usage(result, "--format beancount prints directives")


@pytest.mark.parametrize("command", [".describe 'x", ".set 'x"])
def test_an_unbalanced_quote_in_a_dot_command_is_a_usage_error(books: Path, command: str) -> None:
    on_source = _bea(books, "query", "--source", str(books / "main.bean"), command)
    _assert_one_line_usage(on_source, "No closing quotation")
    on_file = _bea(books, "-f", str(books / "main.bean"), "query", command)
    _assert_one_line_usage(on_file, "No closing quotation")
    assert "ValueError" not in on_file.stderr


def test_a_well_formed_describe_still_answers(books: Path) -> None:
    result = _bea(books, "query", "--source", str(books / "main.bean"), ".describe accounts")
    assert result.returncode == 0, result.stderr
    assert "table accounts:" in result.stdout
