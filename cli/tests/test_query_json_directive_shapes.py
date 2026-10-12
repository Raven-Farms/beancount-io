"""Directives in query JSON carry no Python reprs (w5/104).

`--json query PRINT` dumped each directive field by field with a string
fallback, so machine output held `"Booking.FIFO"`, `"<class 'str'>"` and
`"_tuplegetter(0, …)"` where `bea list` answers a clean, documented shape.
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
option "operating_currency" "USD"
2024-01-01 commodity HOOL
  name: "Hooli"
2024-01-01 open Assets:Cash USD
2024-01-01 open Assets:Broker HOOL "FIFO"
2024-01-01 open Assets:Old USD
2024-01-01 open Expenses:Food
2024-01-01 open Equity:Opening
2024-01-02 pad Assets:Cash Equity:Opening
2024-01-03 balance Assets:Cash  100.00 USD
2024-01-04 custom "budget" Expenses:Food "monthly" 400.00 USD TRUE 2024-01-01 -3.5
2024-01-05 * "Grocer" "Refund (partial)" #food #trip ^receipt
  Expenses:Food  -5.00 USD
  Assets:Cash
2024-01-06 * "Buy"
  Assets:Broker  2 HOOL {10.00 USD}
  Assets:Cash
2024-01-07 price HOOL 11.00 USD
2024-01-08 note Assets:Cash "counted"
2024-01-09 event "location" "Berlin"
2024-01-10 query "food" "SELECT account WHERE account ~ 'Food'"
2024-01-11 close Assets:Old
"""
TYPES = ["commodity", "open", "pad", "balance", "custom", "transaction", "price", "note", "event", "query", "close"]
REPRS = ("<", "_tuplegetter", "Booking.", "object at 0x", "frozenset(", "Decimal(", "datetime.")


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _json(book: Path, *args: str) -> Any:
    result = runner.invoke(app, ["--json", "--file", str(book), *args])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


@pytest.mark.parametrize("directive", TYPES)
def test_every_directive_type_serializes_without_a_python_repr(book: Path, directive: str) -> None:
    rows = _json(book, "query", f"PRINT FROM type = '{directive}'")["rows"]

    assert rows, directive
    text = json.dumps(rows)
    for repr_marker in REPRS:
        assert repr_marker not in text, text
    assert all(isinstance(row[0], dict) and row[0]["date"].startswith("2024-01-") for row in rows)


def test_custom_values_match_what_list_custom_answers(book: Path) -> None:
    (queried,) = _json(book, "query", "PRINT FROM type = 'custom'")["rows"]
    (listed,) = _json(book, "list", "custom")

    assert queried[0]["values"] == listed["values"]
    assert [value["kind"] for value in listed["values"]] == ["account", "text", "amount", "bool", "date", "number"]


def test_an_explicit_booking_method_is_its_ledger_spelling(book: Path) -> None:
    rows = _json(book, "query", "PRINT FROM type = 'open'")["rows"]
    listed = {item["account"]: item["booking"] for item in _json(book, "list", "open")}

    queried = {row[0]["account"]: row[0]["booking"] for row in rows}
    assert queried["Assets:Broker"] == "FIFO" == listed["Assets:Broker"]
    assert queried["Assets:Cash"] is None
