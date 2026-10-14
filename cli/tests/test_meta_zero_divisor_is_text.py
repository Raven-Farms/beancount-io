"""A `--meta` value that reads as a division by zero is stored as text (w5/272).

Unquoted metadata went to Beancount's parser before the "one plain literal"
rule was applied, and upstream segfaults evaluating a zero divisor: the cheque
number `1045/0` killed the engine and `add` exited 4 with "the outcome is
unknown" over a ledger it had not touched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Equity:Opening\n"
    "2026-01-01 open Expenses:Food\n"
)

DINNER = ["add", "transaction", "Dinner", "--date", "2026-02-01", "-p", "Expenses:Food 40 USD", "-p", "Assets:Checking"]


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _json(book: Path, *argv: str) -> Any:
    result = runner.invoke(app, ["--json", "--file", str(book), *argv])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


@pytest.mark.parametrize(
    "value",
    [
        "1045/0",  # the note's cheque number
        "1045/0.00",
        "1045 / 0",
        "5 /0",  # number, blank, then a divisor rather than a currency
        "1/0 USD",
        "1045/(2-2)",  # computed, so no literal-zero guard could see it
    ],
)
def test_a_zero_divisor_in_a_transaction_value_is_the_text_typed(book: Path, value: str) -> None:
    result = runner.invoke(app, ["--json", "--file", str(book), *DINNER, "--meta", f"check:{value}"])

    assert result.exit_code == 0, result.output
    assert "outcome is unknown" not in result.output
    assert json.loads(result.stdout)["data"]["directive"]["meta"] == {"check": value}
    assert f'  check: "{value}"\n' in book.read_text()
    [listed] = _json(book, "list", "transaction")
    assert listed["meta"] == {"check": value}
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_add_commodity_keeps_a_zero_divisor_as_text(book: Path) -> None:
    result = runner.invoke(
        app,
        ["--file", str(book), "add", "commodity", "--date", "2026-01-01", "-c", "HOOL"]
        + ["--meta", "ratio:1/0", "--meta", "lot:100"],
    )

    assert result.exit_code == 0, result.output
    assert '  ratio: "1/0"\n  lot: 100\n' in book.read_text()
    [listed] = _json(book, "list", "commodity")
    assert listed["meta"] == {"ratio": "1/0", "lot": {"kind": "number", "value": "100"}}


def test_an_invalid_key_is_still_reported_for_a_value_beancount_never_reads(book: Path) -> None:
    before = book.read_text()
    result = runner.invoke(app, ["--file", str(book), *DINNER, "--meta", "bad.key:1045/0"])

    assert result.exit_code == 2, result.output
    assert "Invalid --meta key 'bad.key'" in result.output
    assert book.read_text() == before


def test_controls_quoted_text_typed_literals_and_the_posting_refusal(book: Path) -> None:
    # A quoted value was always text, and the plain literals keep their types.
    result = runner.invoke(
        app,
        ["--file", str(book), *DINNER, "--meta", 'check:"1045/0"', "--meta", "count:3", "--meta", "fee:5 USD"]
        + ["--meta", "due:2026/03/01", "--meta", "ok:true"],
    )
    assert result.exit_code == 0, result.output
    assert '  check: "1045/0"\n  count: 3\n  fee: 5 USD\n  due: 2026-03-01\n  ok: TRUE\n' in book.read_text()

    # In a posting the same expression is arithmetic, and is refused by name.
    before = book.read_text()
    refused = runner.invoke(
        app,
        ["--file", str(book), "add", "transaction", "Dinner", "--date", "2026-02-01"]
        + ["-p", "Expenses:Food 40/0 USD", "-p", "Assets:Checking"],
    )
    assert refused.exit_code == 2, refused.output
    assert "Division by zero in 'Expenses:Food 40/0 USD'" in refused.output
    assert book.read_text() == before
