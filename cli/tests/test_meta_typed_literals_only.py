"""An unquoted `--meta` value keeps a native type only when it is one plain literal (w5/128).

The value is read by Beancount's own grammar, which evaluates arithmetic,
normalizes numbers and discards comments: the invoice number `2024-001` was
stored as `2023`, the zip code `02134` as `2134`, the phone number `555-1234`
as `-679`, and a memo lost everything after its `;` — all with exit 0.
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

# The note's fixture command, then the other spellings the grammar rewrites.
TEXT = {
    "invoice": "2024-001",
    "zip": "02134",
    "phone": "555-1234",
    "memo": "12 ; split with Bob",
    "share": "1/3",
    "xmas": "12-25",
    "hours": "24/7",
    "grand": "1,000",
    "glued": "5USD",
    "product": "2*3 USD",
    "padded": "007 USD",
    "mobile": "+15551234567",
    "group": "(5)",
    "trailing": "5.",
    "noted": "2026-03-01 ; paid",
    "flagged": "TRUE ; checked",
}

TYPED = {
    "count": ("3", {"kind": "number", "value": "3"}, "count: 3"),
    "rate": ("1.25", {"kind": "number", "value": "1.25"}, "rate: 1.25"),
    "zero": ("0.50", {"kind": "number", "value": "0.50"}, "zero: 0.50"),
    "owed": ("-5", {"kind": "number", "value": "-5"}, "owed: -5"),
    "due": ("2026-03-01", {"kind": "date", "value": "2026-03-01"}, "due: 2026-03-01"),
    "fee": ("5 USD", {"kind": "amount", "number": "5", "currency": "USD"}, "fee: 5 USD"),
    "ok": ("TRUE", True, "ok: TRUE"),
}


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _add(book: Path, *meta: str) -> Any:
    flags = [part for item in meta for part in ("--meta", item)]
    return runner.invoke(
        app,
        ["--json", "--file", str(book), "add", "transaction", "Dinner", "--date", "2026-02-01"]
        + ["-p", "Expenses:Food 40 USD", "-p", "Assets:Checking", *flags],
    )


def _json(book: Path, *argv: str) -> Any:
    result = runner.invoke(app, ["--json", "--file", str(book), *argv])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


def _bql(book: Path, keys: list[str]) -> list[Any]:
    columns = ", ".join(f"entry_meta('{key}')" for key in keys)
    rows = _json(book, "query", f"SELECT {columns} WHERE account = 'Expenses:Food'")["rows"]
    assert len(rows) == 1
    return list(rows[0])


def test_computed_normalized_and_truncated_values_are_stored_as_the_text_typed(book: Path) -> None:
    result = _add(book, *(f"{key}:{value}" for key, value in TEXT.items()))

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"]["directive"]["meta"] == TEXT
    written = book.read_text()
    for key, value in TEXT.items():
        assert f'  {key}: "{value}"\n' in written
    # Read back, not just echoed: through `list` and through BQL.
    [listed] = _json(book, "list", "transaction")
    assert listed["meta"] == TEXT
    assert _bql(book, list(TEXT)) == list(TEXT.values())
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_plain_literals_keep_their_native_types(book: Path) -> None:
    result = _add(book, *(f"{key}:{typed}" for key, (typed, _, _) in TYPED.items()))

    assert result.exit_code == 0, result.output
    written = book.read_text()
    for _, _, line in TYPED.values():
        assert f"  {line}\n" in written
    [listed] = _json(book, "list", "transaction")
    assert listed["meta"] == {key: tagged for key, (_, tagged, _) in TYPED.items()}
    # BQL sees a number, a date, an amount and a boolean, none of them a string.
    count, rate, _, _, due, fee, ok = _bql(book, list(TYPED))
    assert (count, rate, due, ok) == ("3", "1.25", "2026-03-01", True)
    assert fee == {"number": "5", "currency": "USD"}
    [[total]] = _json(book, "query", "SELECT entry_meta('count') + 1 WHERE account = 'Expenses:Food'")["rows"]
    assert total == "4"


@pytest.mark.parametrize(
    ("typed", "written"),
    [
        ('invoice:"2024-001"', 'invoice: "2024-001"'),
        ('zip:"02134"', 'zip: "02134"'),
        ('memo:"12 ; split with Bob"', 'memo: "12 ; split with Bob"'),
    ],
)
def test_quoted_values_are_unchanged(book: Path, typed: str, written: str) -> None:
    result = _add(book, typed)

    assert result.exit_code == 0, result.output
    assert f"  {written}\n" in book.read_text()


def test_add_commodity_keeps_a_zero_padded_code(book: Path) -> None:
    result = runner.invoke(
        app,
        ["--file", str(book), "add", "commodity", "--date", "2026-01-01", "-c", "HOOL"]
        + ["--meta", "cusip:0123456", "--meta", "lot:100"],
    )

    assert result.exit_code == 0, result.output
    assert '  cusip: "0123456"\n  lot: 100\n' in book.read_text()
    [listed] = _json(book, "list", "commodity")
    assert listed["meta"] == {"cusip": "0123456", "lot": {"kind": "number", "value": "100"}}


def test_bulk_json_text_matches_the_flag(book: Path, tmp_path: Path) -> None:
    rows = [
        {
            "date": "2026-02-01",
            "narration": "Dinner",
            "postings": [
                {"account": "Expenses:Food", "units": {"number": "40", "currency": "USD"}},
                {"account": "Assets:Checking", "units": {"number": "-40", "currency": "USD"}},
            ],
            "meta": {"invoice": "2024-001", "zip": "02134"},
        }
    ]
    batch = tmp_path / "rows.json"
    batch.write_text(json.dumps(rows))
    result = runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(batch)])

    assert result.exit_code == 0, result.output
    assert '  invoice: "2024-001"\n  zip: "02134"\n' in book.read_text()
