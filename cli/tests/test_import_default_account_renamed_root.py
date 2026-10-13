"""The import default counter account follows the ledger's expenses root (w5/151).

The built-in fallback was the literal `Expenses:Uncategorized`. On a ledger
that sets `name_expenses` that root does not exist, so every `--csv` import
was refused with a `--default-account` error although the flag was never
typed, even when a rule matched every row. The engine now derives the default
from the loaded options, and the frontend forwards the flag only when the
caller (or the remembered mapping) supplied one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

RENAMED = """option "operating_currency" "EUR"
option "name_assets" "Aktiva"
option "name_expenses" "Aufwand"
2024-01-01 open Aktiva:Bank EUR
2024-01-01 open Aufwand:Essen EUR
2024-01-01 open Equity:Anfang EUR
2024-01-02 * "Opening"
  Aktiva:Bank  1000.00 EUR
  Equity:Anfang
"""
DEFAULT_ROOTS = """option "operating_currency" "EUR"
2024-01-01 open Assets:Bank EUR
2024-01-01 open Expenses:Uncategorized EUR
"""
CSV = "Date,Amount,Description\n2024-03-06,-40.00,Markt Einkauf\n2024-03-07,-3.00,Kiosk\n"
MAPPING = "date=Date,amount=Amount,narration=Description"
RULES = '[[rule]]\nmatch = "Markt"\naccount = "Aufwand:Essen"\n'


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(RENAMED)
    (tmp_path / "bank.csv").write_text(CSV)
    (tmp_path / "rules.toml").write_text(RULES)
    return path


def _import(ledger: Path, *args: str) -> tuple[int, dict[str, Any]]:
    argv = ["--json", "--no-input", "--file", str(ledger), "import", str(ledger.parent / "bank.csv"), *args]
    result = CliRunner().invoke(app, argv)
    payload = json.loads(result.stdout if result.exit_code == 0 else result.stderr)
    return result.exit_code, payload["data"] if result.exit_code == 0 else payload["error"]


def _counter_accounts(data: dict[str, Any]) -> list[str]:
    return [row["accounts"][1] for row in data["rows"]]


@pytest.mark.parametrize(
    "extra",
    [
        ("--csv", MAPPING, "--rules", "rules.toml"),
        ("--csv", MAPPING),
        ("--csv", "auto"),
    ],
    ids=["rules", "explicit", "auto"],
)
def test_the_default_account_uses_the_renamed_expenses_root(book: Path, extra: tuple[str, ...]) -> None:
    args = [str(book.parent / part) if part == "rules.toml" else part for part in extra]

    code, data = _import(book, *args, "--account", "Aktiva:Bank")

    assert code == 0, data
    matched = "Aufwand:Essen" if "--rules" in extra else "Aufwand:Uncategorized"
    assert _counter_accounts(data) == [matched, "Aufwand:Uncategorized"]
    # The fallback is not open in this ledger, so its row waits on the remedy.
    unmatched = data["rows"][1]
    assert unmatched["status"] == "blocked"
    assert "bea add open --account Aufwand:Uncategorized" in unmatched["reason"]
    assert book.read_text() == RENAMED


def test_apply_and_the_remembered_rerun_post_to_the_renamed_root(book: Path) -> None:
    opened = RENAMED + "2024-01-01 open Aufwand:Uncategorized EUR\n"
    book.write_text(opened)

    code, data = _import(book, "--csv", MAPPING, "--account", "Aktiva:Bank", "--apply")

    assert code == 0, data
    assert data["written"] == 2
    assert book.read_text().count("  Aufwand:Uncategorized ") == 2

    # The flag-free replay has no default account to forward either.
    code, again = _import(book)

    assert code == 0, again
    assert again["config_source"] == "remembered --csv"
    assert again["remembered"]["default_account"] is None
    assert again["duplicates"] == 2
    assert not any("--default-account" in note for note in again["notes"])


def test_an_explicit_default_account_is_unchanged(book: Path) -> None:
    code, data = _import(book, "--csv", MAPPING, "--account", "Aktiva:Bank", "--default-account", "Aufwand:Essen")

    assert code == 0, data
    assert _counter_accounts(data) == ["Aufwand:Essen", "Aufwand:Essen"]
    assert [row["status"] for row in data["rows"]] == ["new", "new"]

    # A typed name under a root the ledger does not use is still the caller's
    # mistake, and the error may name the flag because it was on the line.
    code, error = _import(
        book, "--csv", MAPPING, "--account", "Aktiva:Bank", "--default-account", "Expenses:Uncategorized"
    )

    assert code == 2
    assert error["message"].startswith("--default-account: Account 'Expenses:Uncategorized' has root 'Expenses'")
    assert book.read_text() == RENAMED


def test_a_default_root_ledger_keeps_expenses_uncategorized(book: Path) -> None:
    book.write_text(DEFAULT_ROOTS)

    code, data = _import(book, "--csv", MAPPING, "--account", "Assets:Bank")

    assert code == 0, data
    assert _counter_accounts(data) == ["Expenses:Uncategorized", "Expenses:Uncategorized"]
    assert [row["status"] for row in data["rows"]] == ["new", "new"]
