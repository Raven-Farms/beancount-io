"""A cost or priced posting that forgets its commodity is refused, not defaulted (w5/098).

`3 {80 USD}` was completed with the operating currency and written as
`3 USD {80 USD}` — three dollars held at eighty dollars each — with exit 0
and a passing `bea check`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Brokerage
2026-01-01 open Assets:Hool HOOL
2026-01-01 open Expenses:Food
2026-01-01 open Equity:Opening

2026-01-02 * "Opening"
  Assets:Checking  10000.00 USD
  Equity:Opening
"""


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _add(book: Path, *postings: str) -> Any:
    flags = [part for posting in postings for part in ("-p", posting)]
    return runner.invoke(app, ["--file", str(book), "add", "transaction", "Buy more", "--date", "2026-02-01", *flags])


@pytest.mark.parametrize(
    "posting",
    [
        "Assets:Brokerage 3 {80 USD}",
        "Assets:Brokerage 3 {{240 USD}}",
        "Assets:Brokerage 100 @ 1.08 USD",
        "Assets:Brokerage 100 @@ 108 USD",
        "Assets:Checking 3 {80 USD}",
    ],
    ids=["cost", "total-cost", "price", "total-price", "sole-currency-account"],
)
def test_a_rate_in_the_currency_it_would_default_to_is_refused(book: Path, posting: str) -> None:
    result = _add(book, posting, "Assets:Checking")

    assert result.exit_code == 2, result.output
    flat = " ".join(result.output.split())
    assert "--posting 1" in flat and "Name the commodity" in flat
    assert book.read_text() == LEDGER


@pytest.mark.parametrize(
    "posting",
    [
        "Assets:Brokerage 3 {80}",
        "Assets:Brokerage 3 {}",
        "Assets:Brokerage 3 {80} @ 90 USD",
        "Assets:Brokerage 3 {2026-01-01}",
        'Assets:Brokerage 3 {"x"}',
        "Assets:Brokerage 3 {{240}}",
        "Assets:Checking 3 {80}",
    ],
    ids=["cost", "empty-cost", "cost-and-price", "date-cost", "label-cost", "total-cost", "sole-currency"],
)
def test_a_rate_without_a_currency_is_refused_too(book: Path, posting: str) -> None:
    # w5/800: a rate that names no currency cannot prove it differs from the
    # default, and a price beside a cost was never consulted at all.
    result = _add(book, posting, "Assets:Checking -240.00 USD")

    assert result.exit_code == 2, result.output
    flat = " ".join(result.output.split())
    assert "--posting 1" in flat and "Name the commodity" in flat
    assert book.read_text() == LEDGER


def test_the_commodity_written_out_still_adds_the_lot(book: Path) -> None:
    result = _add(book, "Assets:Brokerage 3 HOOL {80 USD}", "Assets:Checking")

    assert result.exit_code == 0, result.output
    assert "Assets:Brokerage 3 HOOL {80 USD}" in " ".join(book.read_text().split())
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_an_account_opened_for_one_commodity_still_supplies_it(book: Path) -> None:
    result = _add(book, "Assets:Hool 3 {80 USD}", "Assets:Checking")

    assert result.exit_code == 0, result.output
    assert "Assets:Hool 3 HOOL {80 USD}" in " ".join(book.read_text().split())


def test_a_plain_amount_keeps_the_currency_default(book: Path) -> None:
    result = _add(book, "Expenses:Food 5", "Assets:Checking")

    assert result.exit_code == 0, result.output
    assert "Expenses:Food 5 USD" in " ".join(book.read_text().split())
