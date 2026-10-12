"""A `PRINT` that matches no directives is an empty result, not a usage error (w5/102).

With zero rows the format guard fell back to the column's declared type;
`PRINT`'s lone column is typed `object`, so the statement was taken for a
column `SELECT` and refused — with the advice to "use PRINT". A per-year
export of a year with no activity failed, while `--json` returned zero rows.
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
EMPTY = "PRINT FROM year = 2025"


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _query(book: Path, *args: str, as_json: bool = False) -> Any:
    return runner.invoke(app, [*(["--json"] if as_json else []), "--file", str(book), "query", *args])


@pytest.mark.parametrize("flags", [[], ["-f", "beancount"], ["-f", "text"]], ids=["default", "beancount", "text"])
def test_an_empty_print_exits_0_with_no_rows(book: Path, flags: list[str]) -> None:
    result = _query(book, EMPTY, *flags)

    assert result.exit_code == 0, result.output
    assert "(no rows)" in result.stderr
    assert result.stdout == ""


def test_an_empty_print_agrees_with_the_json_mode(book: Path) -> None:
    result = _query(book, EMPTY, as_json=True)

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"]["rows"] == []


def test_an_empty_print_export_writes_an_empty_file(book: Path) -> None:
    out = book.parent / "y2025.bean"

    result = _query(book, EMPTY, "-o", str(out))

    assert result.exit_code == 0, result.output
    assert "(no rows)" in result.stderr
    assert out.read_text() == ""
    assert runner.invoke(app, ["--file", str(out), "check"]).exit_code == 0


def test_a_print_with_entries_still_exports_them(book: Path) -> None:
    out = book.parent / "y2024.bean"

    result = _query(book, "PRINT FROM year = 2024", "-o", str(out))

    assert result.exit_code == 0, result.output
    assert '2024-01-05 * "Grocer" "Refund (partial)"' in out.read_text()


@pytest.mark.parametrize("query", ["SELECT date FROM year = 2025", "SELECT date"], ids=["empty", "with-rows"])
def test_a_column_select_under_the_beancount_format_is_still_a_usage_error(book: Path, query: str) -> None:
    result = _query(book, query, "-f", "beancount")

    assert result.exit_code == 2, result.output
    assert "must return entries" in " ".join(result.output.split())
