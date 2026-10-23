"""Pad hints name the followable next step, and a pad cannot source itself (w5/799).

The staged-pad warning sent the user to `add balance --pad-from`, which the
staged pad itself blocks; a `--pad-from` currency refusal said to record the
synthesized pad leg in another currency, which a pad leg cannot be; and a pad
sourcing its own account staged a pad no balance could complete.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
2026-01-01 open Assets:Savings USD
2026-01-01 open Equity:OpeningBalances
"""


def _bea(book: Path, *args: str) -> Any:
    return runner.invoke(app, ["--file", str(book), *args])


def _flat(result: Any) -> str:
    return " ".join(result.output.split())


def test_staged_pad_warning_names_plain_balance_and_following_it_writes(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "st.bean"
    book.write_text(LEDGER)

    staged = _bea(
        book,
        "add",
        "pad",
        "--date",
        "2026-01-01",
        "-a",
        "Assets:Savings",
        "-s",
        "Equity:OpeningBalances",
        "--allow-errors",
    )
    assert staged.exit_code == 0, staged.output
    assert "Staged: add its balance with bea add balance (without --pad-from), or remove the pad." in _flat(staged)

    balance = _bea(book, "add", "balance", "--date", "2026-01-02", "-a", "Assets:Savings", "--amount", "10.00 USD")
    assert balance.exit_code == 0, balance.output
    assert _bea(book, "check").exit_code == 0


def test_unrelated_refusal_while_staged_names_plain_balance(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "st.bean"
    book.write_text(LEDGER)
    staged = _bea(
        book,
        "add",
        "pad",
        "--date",
        "2026-01-01",
        "-a",
        "Assets:Savings",
        "-s",
        "Equity:OpeningBalances",
        "--allow-errors",
    )
    assert staged.exit_code == 0, staged.output

    result = _bea(book, "add", "note", "--date", "2026-01-06", "-a", "Assets:Savings", "--comment", "hi")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "already has 1 error(s)" in flat
    assert "Staged: add its balance with bea add balance (without --pad-from), or remove the pad." in flat
    assert "atomically" not in flat


def test_pad_from_currency_refusal_names_a_pad_from_that_allows_it(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "cur.bean"
    book.write_text("2026-01-01 open Assets:Checking USD\n2026-01-01 open Equity:EurOnly EUR\n")

    result = _bea(
        book,
        "add",
        "balance",
        "--date",
        "2026-01-10",
        "-a",
        "Assets:Checking",
        "--amount",
        "100.00 USD",
        "--pad-from",
        "Equity:EurOnly",
    )

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "Choose a --pad-from account that allows USD, or edit that open to" in flat
    assert "record this posting in EUR" not in flat
    assert "2026-01-01 open Equity:EurOnly EUR,USD" in flat


def test_existing_pad_currency_refusal_names_the_pad(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "cur.bean"
    book.write_text("2026-01-01 open Assets:Checking USD\n2026-01-01 open Equity:EurOnly EUR\n")
    staged = _bea(
        book,
        "add",
        "pad",
        "--date",
        "2026-01-05",
        "-a",
        "Assets:Checking",
        "-s",
        "Equity:EurOnly",
        "--allow-errors",
    )
    assert staged.exit_code == 0, staged.output

    result = _bea(book, "add", "balance", "--date", "2026-01-10", "-a", "Assets:Checking", "--amount", "100.00 USD")

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert f"synthesized from the pad at {book}:4" in flat
    assert "Remove that pad and pad from an account that allows USD" in flat
    assert "record this posting in EUR" not in flat


def test_padded_account_leg_keeps_the_generic_currency_advice(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "cur.bean"
    book.write_text("2026-01-01 open Assets:Checking USD\n2026-01-01 open Equity:Opening\n")

    result = _bea(
        book,
        "add",
        "balance",
        "--date",
        "2026-01-10",
        "-a",
        "Assets:Checking",
        "--amount",
        "100.00 EUR",
        "--pad-from",
        "Equity:Opening",
    )

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "Choose a --pad-from account" not in flat
    assert "record this posting in USD" in flat


def test_add_pad_from_itself_is_a_usage_error(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "self.bean"
    book.write_text("2026-01-01 open Assets:Checking USD\n")

    result = _bea(
        book,
        "add",
        "pad",
        "--date",
        "2026-01-09",
        "-a",
        "Assets:Checking",
        "-s",
        "Assets:Checking",
        "--allow-errors",
    )

    assert result.exit_code == 2, result.output
    assert "The pad source must be another account" in _flat(result)
    assert "pad Assets:Checking Assets:Checking" not in book.read_text()


def test_add_balance_pad_from_itself_is_a_usage_error(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "self.bean"
    book.write_text("2026-01-01 open Assets:Checking USD\n2026-01-01 open Equity:Opening\n")

    result = _bea(
        book,
        "add",
        "balance",
        "--date",
        "2026-01-10",
        "-a",
        "Assets:Checking",
        "--amount",
        "5.00 USD",
        "--pad-from",
        "Assets:Checking",
    )

    assert result.exit_code == 2, result.output
    assert "The pad source must be another account" in _flat(result)
    assert "pad Assets:Checking Assets:Checking" not in book.read_text()
