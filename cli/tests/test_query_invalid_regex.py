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


@pytest.mark.parametrize(
    "query",
    [
        "SELECT date, narration /* was: narration ~ '(partial' */ WHERE account ~ 'Food'",
        "SELECT date, narration WHERE narration != \"a ~ '[\" AND account ~ 'Food'",
        "SELECT date, narration WHERE account ~ 'Food' /* ~ '[[:alpha:]]' */",
    ],
    ids=["commented-condition", "spliced-across-literals", "posix-class-in-comment"],
)
def test_a_pattern_inside_a_comment_or_literal_is_no_operand(book: Path, query: str) -> None:
    """Only `~`/`!~` in code take a pattern; the check scanned comments and literals too (w5/558)."""
    text = _query(book, query)
    as_json = _query(book, query, as_json=True)

    assert text.exit_code == 0, text.output
    assert "Refund (partial)" in text.output
    assert as_json.exit_code == 0, as_json.output
    assert json.loads(as_json.stdout)["data"]["rows"] == [["2024-01-05", "Refund (partial)"]]


def test_a_real_operand_after_a_literal_holding_a_tilde_is_still_checked(book: Path) -> None:
    result = _query(book, "SELECT date WHERE narration != \"a ~ 'b\" AND narration ~ '(partial'")

    assert result.exit_code == 2, result.output
    assert "'(partial' is not a valid regular expression" in result.output


def test_a_question_tilde_subject_is_not_checked_as_a_pattern(tmp_path: Path, bea_config_dir: Path) -> None:
    """`?~` takes its pattern on the left; the right literal is the subject (w5/747)."""
    ledger = tmp_path / "qm.bean"
    ledger.write_text(
        'option "operating_currency" "USD"\n'
        "2026-01-01 open Assets:Cash\n"
        "2026-01-01 open Expenses:Books\n"
        '2026-01-05 txn "Primer"\n'
        "  Expenses:Books 10.00 USD\n"
        "  Assets:Cash\n"
        '2026-01-06 txn "Cookbook"\n'
        "  Expenses:Books 20.00 USD\n"
        "  Assets:Cash\n"
    )

    result = _query(
        ledger,
        "SELECT date, narration WHERE account = 'Expenses:Books' AND narration ?~ 'POS 1234 Primer (Bookshop'",
    )

    assert result.exit_code == 0, result.output
    assert "Primer" in result.output and "Cookbook" not in result.output


def test_a_concatenated_tilde_pattern_runs(book: Path) -> None:
    """Only the whole `+` chain is the pattern; its fragments are not (w5/747)."""
    result = _query(book, "SELECT DISTINCT account WHERE account ~ '^(' + 'Assets|Expenses' + '):'")

    assert result.exit_code == 0, result.output
    assert "Assets:Cash" in result.output and "Expenses:Food" in result.output


def test_a_concatenated_pattern_that_stays_invalid_fails_when_it_runs(book: Path) -> None:
    """Skipping the fragments must not lose the refusal: the whole still compiles (w5/747)."""
    result = _query(book, "SELECT DISTINCT account WHERE account ~ '^(' + '(['")

    assert result.exit_code == 2, result.output
    assert "not a valid regular expression" in result.output


@pytest.mark.parametrize("window", ["", "FROM year = 2025 "], ids=["rows-scanned", "empty-window"])
def test_a_literal_pattern_left_of_question_tilde_is_checked(book: Path, window: str) -> None:
    """A constant `?~` pattern is refused before anything runs, rows or none (w5/747)."""
    result = _query(book, f"SELECT date {window}WHERE '(' ?~ narration")

    assert result.exit_code == 2, result.output
    assert "'(' is not a valid regular expression" in result.output
