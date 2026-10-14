"""A comment after the closing `;` is not a second statement (w5/262).

`SELECT …; /* note */` is one statement to Beanquery, but both statement
guards counted the comment-only tail and refused the query with exit 2: the
frontend's `_split_statements` for one-shots by argument, stdin and
`--source`, and the engine's `_refuse_statement_tail` for stored `query`
directives replayed through `.run`.

A fragment of only whitespace and comments is no statement; anything else
after a `;` — a second query, a bare literal — still is.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bea_engine import protocol
from bea_engine.query import _refuse_statement_tail
from cli.commands.query import _split_statements

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD
2026-01-01 open Expenses:Food USD
2026-01-02 * "Opening"
  Assets:Cash        1000.00 USD
  Equity:Opening    -1000.00 USD
2026-02-10 * "Lunch"
  Expenses:Food        10.00 USD
  Assets:Cash         -10.00 USD
2026-02-11 query "tail" "SELECT account FROM accounts ORDER BY account LIMIT 2; /* c */"
2026-02-11 query "two" "SELECT account FROM accounts ORDER BY account LIMIT 2; /* c */ SELECT 1"
"""

QUERY = "SELECT account FROM accounts ORDER BY account LIMIT 2"
ROWS = [["Assets:Cash"], ["Equity:Opening"]]

ONE = [
    pytest.param("SELECT 1; /* c */", id="comment-after-terminator"),
    pytest.param("SELECT 1;\n  /* c */\n", id="comment-on-next-line"),
    pytest.param("SELECT 1; /* c */ ; /* d */;", id="several-comment-tails"),
    pytest.param("SELECT 1; /* it's; fine */", id="punctuation-in-the-tail"),
    pytest.param("SELECT 1; /* unterminated", id="unterminated-comment-tail"),
    pytest.param("SELECT 1 /* c */;", id="control-comment-before-terminator"),
]

TWO = [
    pytest.param("SELECT 1; SELECT 2", id="plain"),
    pytest.param("SELECT 1; /* c */ SELECT 2", id="comment-then-statement"),
    pytest.param("SELECT 1; SELECT 2 /* c */", id="statement-then-comment"),
    pytest.param("SELECT 1; /* c */ 'x'", id="comment-then-literal"),
    pytest.param("SELECT 1; ''", id="empty-literal"),
]


def _engine_refuses(query: str) -> bool:
    try:
        _refuse_statement_tail(query)
    except protocol.UsageError:
        return True
    return False


@pytest.mark.parametrize("query", ONE)
def test_a_comment_only_fragment_is_not_a_statement(query: str) -> None:
    assert len(_split_statements(query)) == 1, _split_statements(query)
    assert not _engine_refuses(query)


@pytest.mark.parametrize("query", TWO)
def test_a_fragment_with_code_is_still_a_statement(query: str) -> None:
    assert len(_split_statements(query)) == 2, _split_statements(query)
    assert _engine_refuses(query)


def _bea(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        input=stdin,
        stdin=subprocess.DEVNULL if stdin is None else None,
    )


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def test_the_reported_query_runs(tmp_path: Path, ledger: Path) -> None:
    done = _bea(tmp_path, "-f", str(ledger), "query", f"{QUERY}; /* c */")

    assert done.returncode == 0, done.stderr
    assert [line.strip() for line in done.stdout.splitlines()[2:]] == ["Assets:Cash", "Equity:Opening"]


def test_the_reported_query_runs_as_json(tmp_path: Path, ledger: Path) -> None:
    done = _bea(tmp_path, "--json", "-f", str(ledger), "query", f"{QUERY}; /* c */")

    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["data"]["rows"] == ROWS


def test_the_reported_query_runs_from_stdin(tmp_path: Path, ledger: Path) -> None:
    done = _bea(tmp_path, "--json", "-f", str(ledger), "query", stdin=f"{QUERY};\n/* c */\n")

    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["data"]["rows"] == ROWS


def test_the_reported_query_runs_against_a_source(tmp_path: Path, ledger: Path) -> None:
    done = _bea(tmp_path, "query", "--source", str(ledger), "SELECT DISTINCT account ORDER BY account LIMIT 2; /* c */")

    assert done.returncode == 0, done.stderr
    assert "Assets:Cash" in done.stdout


def test_the_comment_before_the_terminator_still_runs(tmp_path: Path, ledger: Path) -> None:
    """The note's control."""
    done = _bea(tmp_path, "--json", "-f", str(ledger), "query", f"{QUERY} /* c */;")

    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["data"]["rows"] == ROWS


@pytest.mark.parametrize("tail", ["; " + QUERY, "; /* c */ " + QUERY])
def test_two_real_statements_are_still_refused(tmp_path: Path, ledger: Path, tail: str) -> None:
    done = _bea(tmp_path, "-f", str(ledger), "query", QUERY + tail)

    assert done.returncode == 2, done.stdout
    assert done.stdout == ""
    assert "One BQL statement per invocation; got 2." in done.stderr


def test_a_stored_query_with_a_comment_tail_runs(tmp_path: Path, ledger: Path) -> None:
    """The engine twin: `.run` replays the directive's text through its own guard."""
    done = _bea(tmp_path, "-f", str(ledger), "query", ".run tail")

    assert done.returncode == 0, done.stderr
    assert [line.strip() for line in done.stdout.splitlines()[2:]] == ["Assets:Cash", "Equity:Opening"]


def test_a_stored_query_with_two_statements_is_still_refused(tmp_path: Path, ledger: Path) -> None:
    done = _bea(tmp_path, "-f", str(ledger), "query", ".run two")

    assert done.returncode == 2, done.stdout
    assert "One BQL statement per query; got 2." in done.stderr
