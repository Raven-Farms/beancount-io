r"""The forced-string form `--meta 'key:"…"'` stores the text between the quotes (w5/232).

The quoted value was read as a Beancount string literal with C-style escapes,
so `"C:\Users\tian\receipts\feb\new.pdf"` was stored with a tab, a newline and
a form feed in it and no other backslash, and `"INV-\d+"` as `INV-d+`, exit 0.
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

PATH = r"C:\Users\tian\receipts\feb\new.pdf"
# How the writer spells that path in the ledger: each backslash doubled.
PATH_LINE = r'"C:\\Users\\tian\\receipts\\feb\\new.pdf"'


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _add(book: Path, *meta: str) -> Any:
    flags = [part for item in meta for part in ("--meta", item)]
    return runner.invoke(
        app,
        ["--json", "--file", str(book), "add", "transaction", "Scan", "--date", "2026-02-01"]
        + ["-p", "Expenses:Food 5 USD", "-p", "Assets:Checking", *flags],
    )


def _json(book: Path, *argv: str) -> Any:
    result = runner.invoke(app, ["--json", "--file", str(book), *argv])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


def test_a_quoted_value_keeps_every_backslash_like_the_bare_form(book: Path) -> None:
    result = _add(book, f'receipt:"{PATH}"', r'pattern:"INV-\d+"', f"bare:{PATH}")

    assert result.exit_code == 0, result.output
    expected = {"receipt": PATH, "pattern": r"INV-\d+", "bare": PATH}
    assert json.loads(result.stdout)["data"]["directive"]["meta"] == expected
    written = book.read_text()
    assert f"  receipt: {PATH_LINE}\n" in written
    assert '  pattern: "INV-\\\\d+"\n' in written
    assert f"  bare: {PATH_LINE}\n" in written
    # Read back, not just echoed.
    [listed] = _json(book, "list", "transaction")
    assert listed["meta"] == expected
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ('code:"1234"', "1234"),
        ('note:""', ""),
        ('memo:"12 ; split with Bob"', "12 ; split with Bob"),
        (r'said:"say \"hi\""', 'say "hi"'),
        # The ledger's own spelling of a path reads back as that path.
        (f"copied:{PATH_LINE}", PATH),
        (r'unc:"\\\\host\\share"', r"\\host\share"),
        (r'tail:"C:\\dir\\"', "C:\\dir\\"),
    ],
)
def test_quoted_strings_and_the_two_escapes(book: Path, typed: str, stored: str) -> None:
    result = _add(book, typed)

    assert result.exit_code == 0, result.output
    key = typed.partition(":")[0]
    assert json.loads(result.stdout)["data"]["directive"]["meta"] == {key: stored}
    [listed] = _json(book, "list", "transaction")
    assert listed["meta"] == {key: stored}


def test_an_unclosed_quoted_value_is_still_refused(book: Path) -> None:
    result = _add(book, r'receipt:"C:\dir\"')

    assert result.exit_code == 2, result.output
    assert "close the quoted string" in result.output
    assert book.read_text() == LEDGER


def test_add_commodity_keeps_a_quoted_path(book: Path) -> None:
    result = runner.invoke(
        app,
        ["--file", str(book), "add", "commodity", "--date", "2026-01-01", "-c", "HOOL", "--meta", f'doc:"{PATH}"'],
    )

    assert result.exit_code == 0, result.output
    assert f"  doc: {PATH_LINE}\n" in book.read_text()
    [listed] = _json(book, "list", "commodity")
    assert listed["meta"] == {"doc": PATH}


def test_bulk_json_text_matches_the_quoted_flag(book: Path, tmp_path: Path) -> None:
    rows = [
        {
            "date": "2026-02-01",
            "narration": "Scan",
            "postings": [
                {"account": "Expenses:Food", "units": {"number": "5", "currency": "USD"}},
                {"account": "Assets:Checking", "units": {"number": "-5", "currency": "USD"}},
            ],
            "meta": {"receipt": PATH},
        }
    ]
    batch = tmp_path / "rows.json"
    batch.write_text(json.dumps(rows))
    result = runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(batch)])

    assert result.exit_code == 0, result.output
    assert f"  receipt: {PATH_LINE}\n" in book.read_text()
