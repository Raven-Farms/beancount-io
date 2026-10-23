"""Refusals blame a guessed operating currency instead of advising an exchange (w5/804).

`Expenses:Food 10` beside `-10 EUR` reads as `10 USD`, and the refusal
advised a currency exchange the user never made. When exactly one posting
was defaulted and spelling out the residual's other currency fixes the
balance, the hint names the guess and suggests it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Euro EUR
2026-01-01 open Assets:Cash USD
2026-01-01 open Assets:Broker
2026-01-01 open Expenses:Food
2026-01-01 open Expenses:Narrow USD,GBP
2026-01-01 open Expenses:Wide USD,EUR
"""


def _add(book: Path, *postings: str) -> Any:
    flags = [part for posting in postings for part in ("-p", posting)]
    return runner.invoke(
        app, ["--file", str(book), "add", "transaction", "Lunch in Paris", "--date", "2026-02-01", *flags]
    )


def _flat(result: Any) -> str:
    return " ".join(result.output.split())


def _book(tmp_path: Path) -> Path:
    book = tmp_path / "fx.bean"
    book.write_text(LEDGER)
    return book


def test_unbalanced_default_names_the_guess_and_suggests_the_currency(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Expenses:Food 10", "Assets:Euro -10 EUR")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "Expenses:Food 10 was read as 10 USD (the operating currency)" in flat
    assert "write 'Expenses:Food 10 EUR' instead" in flat
    assert "currency exchange" not in flat
    assert book.read_text() == LEDGER

    followed = _add(book, "Expenses:Food 10 EUR", "Assets:Euro -10 EUR")
    assert followed.exit_code == 0, followed.output


def test_interpolated_fill_from_a_default_names_the_guess(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Expenses:Food 10", "Assets:Euro")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "That USD came from 'Expenses:Food 10', read as 10 USD (the operating currency)" in flat
    assert "write 'Expenses:Food 10 EUR' instead" in flat
    assert "price the USD leg" not in flat
    assert book.read_text() == LEDGER

    followed = _add(book, "Expenses:Food 10 EUR", "Assets:Euro")
    assert followed.exit_code == 0, followed.output


def test_explicit_currencies_keep_the_exchange_advice(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Expenses:Food 10 USD", "Assets:Euro -10 EUR")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "For a currency exchange" in flat
    assert "was read as" not in flat


def test_explicit_fill_keeps_the_pricing_advice(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Expenses:Food 10 USD", "Assets:Euro")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "price the USD leg at the rate paid" in flat
    assert "was read as" not in flat


def test_forced_single_currency_default_keeps_the_exchange_advice(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Assets:Checking 10", "Assets:Euro -10 EUR")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "For a currency exchange" in flat
    assert "was read as" not in flat


def test_partial_residual_keeps_the_exchange_advice(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Expenses:Food 10", "Assets:Euro -5 EUR", "Assets:Cash -5 USD")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "For a currency exchange" in flat
    assert "was read as" not in flat


def test_balanced_extra_legs_still_redirect(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Expenses:Food 10", "Assets:Euro -10 EUR", "Assets:Checking 5 USD", "Assets:Cash -5 USD")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "Expenses:Food 10 was read as 10 USD (the operating currency)" in flat
    assert "write 'Expenses:Food 10 EUR' instead" in flat

    followed = _add(book, "Expenses:Food 10 EUR", "Assets:Euro -10 EUR", "Assets:Checking 5 USD", "Assets:Cash -5 USD")
    assert followed.exit_code == 0, followed.output


def test_allowed_multi_currency_account_redirects(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Expenses:Wide 10", "Assets:Euro -10 EUR")

    assert result.exit_code == 1, result.output
    assert "Expenses:Wide 10 was read as 10 USD (the operating currency)" in _flat(result)


def test_disallowed_currency_keeps_the_exchange_advice(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Expenses:Narrow 10", "Assets:Euro -10 EUR")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "For a currency exchange" in flat
    assert "was read as" not in flat


def test_cost_legs_keep_the_exchange_advice(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _book(tmp_path)

    result = _add(book, "Expenses:Food 10", "Assets:Broker 1 HOOL {100 USD}", "Assets:Euro -110 EUR")

    assert result.exit_code == 1, result.output
    assert "For a currency exchange" in _flat(result)
