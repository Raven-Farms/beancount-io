"""Native `query --source` refuses a ledger path the loader would expand (w5/791).

Beancount's loader runs `expandvars` on the root path, so `--source
'x$HOME/m.bean'` silently queried `x/Users/<user>/m.bean` — another ledger —
with exit 0, and a `--source` whose expansion names nothing answered from an
empty database and replaced an `--output` export with a header row. The same
`$VAR` under `--file` already exits 2 (w5/315, w5/579); `--source` refused
neither. A `csv:` source is opened directly, so it keeps loading literally.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Equity:Opening USD
2024-01-02 * "{narration}"
  Expenses:Food  12.50 USD
  Assets:Cash
"""
QUERY = "SELECT narration"
PREVIOUS = b"narration\nreal\n"
UNSET = "BEA_QA_791_DEFINITELY_UNSET"


@pytest.fixture
def books(tmp_path: Path) -> Path:
    literal = tmp_path / "x$HOME"
    literal.mkdir()
    (literal / "m.bean").write_text(LEDGER.format(narration="real"))
    expanded = tmp_path / "x" / os.environ["HOME"].lstrip("/")
    expanded.mkdir(parents=True)
    (expanded / "m.bean").write_text(LEDGER.format(narration="OTHER LEDGER"))
    (tmp_path / "b$HOME.bean").write_text(LEDGER.format(narration="lonely"))
    (tmp_path / "report.csv").write_bytes(PREVIOUS)
    return tmp_path


def _run(books: Path, module: str, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", module, *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(books, "cli.main", "--no-input", *args)


@pytest.mark.parametrize("spelling", ["x$HOME/m.bean", "beancount:x$HOME/m.bean"], ids=["bare", "uri"])
def test_expanding_source_is_refused_before_anything_reads(books: Path, spelling: str) -> None:
    result = _bea(books, "query", "--source", spelling, QUERY, "-f", "csv", "-o", "report.csv")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "contains an environment variable that Beancount would expand" in result.stderr.replace("\n", "")
    assert spelling in result.stderr.replace("\n", "")
    assert "Traceback" not in result.stderr
    assert result.stdout == ""
    assert (books / "report.csv").read_bytes() == PREVIOUS


def test_expanding_source_to_nothing_keeps_the_export(books: Path) -> None:
    result = _bea(books, "query", "--source", "b$HOME.bean", QUERY, "-f", "csv", "-o", "report.csv")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "contains an environment variable that Beancount would expand" in result.stderr.replace("\n", "")
    assert (books / "report.csv").read_bytes() == PREVIOUS


def test_engine_refuses_the_expanding_root_itself(books: Path) -> None:
    """The backstop: the helper, run without the frontend's check in front of it."""
    result = _run(
        books,
        "bea_engine",
        "source-query",
        "--format",
        "csv",
        "--output",
        str(books / "report.csv"),
        "x$HOME/m.bean",
        QUERY,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert (
        "error: Ledger path 'x$HOME/m.bean' (from --source) contains an environment variable"
        in result.stderr.replace("\n", "")
    )
    assert "Traceback" not in result.stderr
    assert (books / "report.csv").read_bytes() == PREVIOUS


def test_engine_shell_refuses_the_expanding_root(books: Path) -> None:
    result = _run(books, "bea_engine", "source-shell", "x$HOME/m.bean")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "contains an environment variable that Beancount would expand" in result.stderr.replace("\n", "")
    assert result.stdout == ""


def test_unset_variable_falls_through_to_the_missing_file(books: Path) -> None:
    result = _bea(books, "query", "--source", f"${UNSET}/x.bean", QUERY)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "would expand" not in result.stderr
    assert "No ledger file at " in result.stderr


def test_csv_source_with_a_variable_loads_literally(books: Path) -> None:
    (books / "c$HOME").mkdir()
    (books / "c$HOME" / "t.csv").write_text("a,b\n1,2\n")
    result = _bea(books, "query", "--source", "csv:c$HOME/t.csv", "SELECT a FROM t")

    assert result.returncode == 0, result.stderr
    assert "1" in result.stdout.split()
