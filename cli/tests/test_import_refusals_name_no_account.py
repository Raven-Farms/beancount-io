"""Import refusals never suggest an account or columns nobody typed (w5/612).

w5/470 made the no-importer refusal keep the typed account and list the
file's columns. Three other refusals still said `--account Assets:Checking`
and `date=Date,amount=Amount,narration=Description`: followed, a savings
export went into checking, or the pasted mapping named columns the file
lacked.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Assets:Savings USD\n"
    "2026-01-01 open Income:Interest USD\n"
    "2026-01-01 open Expenses:Uncategorized USD\n"
)


@pytest.fixture
def books(tmp_path: Path, bea_config_dir: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "savings.csv").write_text("Posted Date,Memo,Debit,Credit\n07/31/2026,INTEREST PAYMENT,,8.25\n")
    (tmp_path / "partial.csv").write_text("Date,What,HowMuch\n2026-02-01,A,-1.00\n")
    return tmp_path


def _refusal(books: Path, *args: str) -> str:
    result = runner.invoke(app, ["--no-input", "--file", str(books / "main.bean"), "import", *args])
    assert result.exit_code == 2, result.output
    return " ".join(result.stderr.split())


@pytest.mark.parametrize(
    "args",
    [["savings.csv"], ["savings.csv", "--csv", "date=Posted Date,debit=Debit,credit=Credit,narration=Memo"]],
    ids=["inferred-mapping", "typed-mapping"],
)
def test_a_missing_account_is_a_placeholder(books: Path, args: list[str]) -> None:
    message = _refusal(books, str(books / args[0]), *args[1:])

    assert "--account ACCOUNT" in message
    assert "Assets:Checking" not in message


@pytest.mark.parametrize(
    ("args", "account"),
    [(["--account", "Assets:Savings"], "Assets:Savings"), (["--csv", "auto"], "ACCOUNT")],
    ids=["typed-account", "no-account"],
)
def test_an_unread_header_names_its_own_columns(books: Path, args: list[str], account: str) -> None:
    message = _refusal(books, str(books / "partial.csv"), *args)

    assert "Its columns are: Date, What, HowMuch." in message
    assert f"Name them with --csv date=COLUMN,amount=COLUMN,narration=COLUMN --account {account}." in message
    assert "amount=Amount" not in message
