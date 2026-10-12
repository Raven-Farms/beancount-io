"""A malformed regex in a BQL query is a usage error, whether or not a row is scanned (w5/103).

Beanquery compiles a `~` pattern while evaluating rows, so the `re.error`
escaped as exit 1, category `validation` — the code for a broken ledger — with
a message naming neither the pattern nor the query. The same query exited 0
when its window held no rows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food
2024-01-05 * "Grocer" "Refund (partial)" #food
  Expenses:Food  -5.00 USD
  Assets:Cash
"""


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _query(book: Path, query: str, *, as_json: bool = False) -> Any:
    return runner.invoke(app, [*(["--json"] if as_json else []), "--file", str(book), "query", query])


@pytest.mark.parametrize("pattern", ["(partial", "[", "*sale"])
@pytest.mark.parametrize("window", ["", "FROM year = 2025 "], ids=["rows-scanned", "empty-window"])
@pytest.mark.parametrize("operator", ["~", "!~"])
def test_a_malformed_pattern_is_a_usage_error_naming_it(book: Path, pattern: str, window: str, operator: str) -> None:
    query = f"SELECT date, narration {window}WHERE narration {operator} '{pattern}'"

    text = _query(book, query)
    as_json = _query(book, query, as_json=True)

    assert text.exit_code == 2, text.output
    assert repr(pattern) in text.output and "not a valid regular expression" in text.output
    error = json.loads(as_json.stderr)["error"]
    assert (error["category"], error["exit_code"]) == ("usage", 2)
    assert pattern in error["message"]
    assert any(query in line for line in error["details"])


def test_a_double_quoted_pattern_is_checked_too(book: Path) -> None:
    result = _query(book, 'SELECT date WHERE narration ~ "(partial"')

    assert result.exit_code == 2, result.output


@pytest.mark.parametrize(
    "query",
    [
        "SELECT date, narration WHERE narration ~ '\\(partial'",
        "SELECT date WHERE narration ~ 'Refund' AND payee !~ 'Nobody'",
        "SELECT date WHERE narration = '(partial'",
    ],
    ids=["escaped", "two-valid-patterns", "equality-is-not-a-pattern"],
)
def test_valid_queries_are_unchanged(book: Path, query: str) -> None:
    result = _query(book, query)

    assert result.exit_code == 0, result.output
