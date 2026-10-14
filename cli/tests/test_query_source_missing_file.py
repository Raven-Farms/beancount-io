"""Native `query --source` refuses a ledger file that is not there (w5/249).

Upstream records `File "…" does not exist` as one more load error and answers
from an empty database, so a typo in the `--source` path exited 0 and replaced
an existing `--output` export with a header row; under `-q` it said nothing at
all. The same typo with `--file` exits 2. The frontend now refuses the path
before the engine starts, and the engine refuses the path it would really hand
the loader, which covers the spellings the two sides read differently.
Load errors inside a ledger that exists keep upstream's behaviour.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.query_terminal import QueryTerminal

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Equity:Opening USD
2024-01-02 * "Open"
  Assets:Cash  100.00 USD
  Equity:Opening
2024-01-03 * "Lunch"
  Expenses:Food  12.50 USD
  Assets:Cash
"""
QUERY = "SELECT account, sum(position) GROUP BY account ORDER BY account"
PREVIOUS = b"account,sum(position)\nAssets:Cash,1.00 USD\n"


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.beancount").write_text(LEDGER)
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


@pytest.mark.parametrize(
    ("spelling", "named"),
    [
        ("{books}/mian.beancount", "{books}/mian.beancount"),
        ("mian.beancount", "mian.beancount"),
        ("beancount:{books}/mian.beancount", "{books}/mian.beancount"),
        # The frontend case-folds the scheme, the engine does not: a file name.
        ("Beancount:main.beancount", "Beancount:main.beancount"),
    ],
    ids=["absolute", "relative", "uri", "mixed-case-scheme"],
)
@pytest.mark.parametrize("quiet", [False, True], ids=["errors", "no-errors"])
def test_missing_source_exits_2_and_keeps_the_export(books: Path, spelling: str, named: str, quiet: bool) -> None:
    source = spelling.format(books=books)
    flags = ["-q"] if quiet else []
    result = _bea(books, "query", *flags, "--source", source, QUERY, "-f", "csv", "-o", "report.csv")

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"No ledger file at '{named.format(books=books)}' (from --source" in result.stderr.replace("\n", "")
    assert "Traceback" not in result.stderr
    assert result.stdout == ""
    assert (books / "report.csv").read_bytes() == PREVIOUS


def test_missing_source_without_an_export_exits_2(books: Path) -> None:
    result = _bea(books, "query", "--source", "mian.beancount", QUERY)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "No ledger file at 'mian.beancount'" in result.stderr
    assert result.stdout == ""


def test_directory_source_exits_2_without_a_traceback(books: Path) -> None:
    result = _bea(books, "query", "--source", str(books), QUERY, "-f", "csv", "-o", "report.csv")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "is a directory; expected a ledger file" in result.stderr.replace("\n", "")
    assert "Traceback" not in result.stderr
    assert (books / "report.csv").read_bytes() == PREVIOUS


def test_name_the_url_parser_cuts_short_is_refused_by_its_loaded_path(books: Path) -> None:
    # `a#b.beancount` exists, but upstream loads the URL path, `a`.
    (books / "a#b.beancount").write_text(LEDGER)
    result = _bea(books, "query", "--source", "a#b.beancount", QUERY, "-f", "csv", "-o", "report.csv")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "No ledger file at 'a' (from --source a#b.beancount)" in result.stderr.replace("\n", "")
    assert (books / "report.csv").read_bytes() == PREVIOUS


@pytest.mark.parametrize(
    ("source", "named"),
    [("mian.beancount", "mian.beancount"), ("Beancount:main.beancount", "Beancount:main.beancount"), ("a#b", "a")],
    ids=["typo", "mixed-case-scheme", "fragment"],
)
def test_engine_refuses_the_missing_root_itself(books: Path, source: str, named: str) -> None:
    """The backstop: the helper, run without the frontend's check in front of it."""
    result = _run(
        books, "bea_engine", "source-query", "--format", "csv", "--output", str(books / "report.csv"), source, QUERY
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"error: No ledger file at '{named}' (from --source)." in result.stderr
    assert "Traceback" not in result.stderr
    assert (books / "report.csv").read_bytes() == PREVIOUS


def test_engine_shell_refuses_the_missing_root(books: Path) -> None:
    result = _run(books, "bea_engine", "source-shell", "mian.beancount")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "No ledger file at 'mian.beancount' (from --source)." in result.stderr
    assert result.stdout == ""


def test_interactive_missing_source_never_opens_a_prompt(books: Path) -> None:
    with QueryTerminal(books, ["query", "--source", "mian.beancount"]) as shell:
        screen = shell.read()
        assert shell.process.wait(timeout=10) == 2
    assert "No ledger file at 'mian.beancount'" in screen.replace("\n", "")
    assert "beanquery>" not in screen


@pytest.mark.parametrize("spelling", ["{books}/main.beancount", "main.beancount", "beancount:main.beancount"])
def test_existing_source_still_replaces_the_export(books: Path, spelling: str) -> None:
    source = spelling.format(books=books)
    result = _bea(books, "query", "--source", source, QUERY, "-f", "csv", "-o", "report.csv")

    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""
    # Upstream pads the amounts; the cells are what matters here.
    assert [[cell.strip() for cell in line.split(",")] for line in (books / "report.csv").read_text().splitlines()] == [
        ["account", "sum(position)"],
        ["Assets:Cash", "87.50 USD"],
        ["Equity:Opening", "-100.00 USD"],
        ["Expenses:Food", "12.50 USD"],
    ]


def test_load_errors_in_an_existing_source_keep_upstream_behaviour(books: Path) -> None:
    (books / "main.beancount").write_text(LEDGER + '2024-01-04 * "Bad"\n  Assets:Nope  1 USD\n  Assets:Cash\n')
    result = _bea(books, "query", "--source", "main.beancount", QUERY, "-f", "csv", "-o", "report.csv")

    assert result.returncode == 0, result.stderr
    assert "Invalid reference to unknown account 'Assets:Nope'" in result.stderr
    assert "Assets:Nope," in (books / "report.csv").read_text()


def test_csv_source_is_not_held_to_the_ledger_rule(books: Path) -> None:
    (books / "t.csv").write_text("a,b\n1,2\n")
    result = _bea(books, "query", "--source", "csv:t.csv", "SELECT a FROM t")

    assert result.returncode == 0, result.stderr
    assert "1" in result.stdout.split()
