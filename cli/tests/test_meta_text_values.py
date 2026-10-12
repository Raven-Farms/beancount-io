"""An unquoted `--meta` value the lexer happens to recognize is still the text typed (w5/082).

`check:#1042` lexed as a tag and was stored as `"1042"`; `cc:NULL` wrote an
empty value; and `name:Chase:Sapphire` was refused with a message blaming the
key, because the key's name appeared inside "Invalid account name: …".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food\n'


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _add(book: Path, *meta: str) -> Any:
    flags = [part for item in meta for part in ("--meta", item)]
    return runner.invoke(
        app,
        ["--json", "--file", str(book), "add", "transaction", "x", "--date", "2026-02-01"]
        + ["-p", "Expenses:Food 5 USD", "-p", "Assets:Checking", *flags],
    )


@pytest.mark.parametrize(
    ("typed", "written"),
    [
        ("check:#1042", 'check: "#1042"'),
        ("channel:#general", 'channel: "#general"'),
        ("name:Chase:Sapphire", 'name: "Chase:Sapphire"'),
        ("card:Chase:Sapphire", 'card: "Chase:Sapphire"'),
        ("cc:NULL", 'cc: "NULL"'),
        ("gg:^link", 'gg: "^link"'),
        ("acct:Assets:Checking", 'acct: "Assets:Checking"'),
        ("cur:USD", 'cur: "USD"'),
        ("free:hello world", 'free: "hello world"'),
    ],
)
def test_bare_text_is_stored_as_typed(book: Path, typed: str, written: str) -> None:
    result = _add(book, typed)

    assert result.exit_code == 0, result.output
    assert f"  {written}\n" in book.read_text()
    key, _, value = typed.partition(":")
    assert json.loads(result.stdout)["data"]["directive"]["meta"][key] == value
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


@pytest.mark.parametrize(
    ("typed", "written"),
    [
        ("num:12.5", "num: 12.5"),
        ("ok:true", "ok: TRUE"),
        ("day:2026-01-05", "day: 2026-01-05"),
        ("amt:5 USD", "amt: 5 USD"),
        ('quoted:"#1042"', 'quoted: "#1042"'),
        ('digits:"12.5"', 'digits: "12.5"'),
    ],
)
def test_documented_typed_values_and_quoted_strings_are_unchanged(book: Path, typed: str, written: str) -> None:
    result = _add(book, typed)

    assert result.exit_code == 0, result.output
    assert f"  {written}\n" in book.read_text()


def test_add_commodity_stores_the_same_text(book: Path) -> None:
    result = runner.invoke(
        app, ["--file", str(book), "add", "commodity", "--date", "2026-01-01", "-c", "HOOL", "--meta", "issue:#12"]
    )

    assert result.exit_code == 0, result.output
    assert '  issue: "#12"\n' in book.read_text()


def test_an_unclosed_quote_is_still_refused_as_a_value_problem(book: Path) -> None:
    result = _add(book, 'name:"unclosed')

    assert result.exit_code == 2, result.output
    assert "close the quoted string" in result.output
    assert "Invalid --meta key" not in result.output
    assert book.read_text() == LEDGER
