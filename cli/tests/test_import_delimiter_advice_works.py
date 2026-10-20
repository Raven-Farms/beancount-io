"""Delimiter advice names the separator that splits the header, in the spelling it was given (w5/845).

w5/622's advice named the first separator found (`,` in `Date;Payee, Name;Amount`),
so following it failed on "lacks"; and a delimiter set by `--csv …,delimiter=`
was told "Pass --delimiter X", which then refused as conflicting.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n'
MIXED = "Date;Payee, Name;Amount\n2026-04-01;Coffee, Inc;-4.50\n"
SEMI = "Date;Description;Amount\n2026-04-01;Coffee;-4.50\n"


def _import(tmp_path: Path, name: str, text: str, *args: str) -> tuple[int, str]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / name).write_text(text)
    result = runner.invoke(
        app,
        ["--no-input", "--file", str(ledger), "import", str(tmp_path / name), "--account", "Assets:Checking"]
        + ["--default-account", "Expenses:Food", *args],
    )
    assert ledger.read_text() == LEDGER
    return result.exit_code, " ".join((result.stdout + result.stderr).split())


@pytest.mark.parametrize(
    "csv",
    ['date=Date,amount=Amount,payee="Payee, Name"', "auto"],
    ids=["mapping", "auto"],
)
def test_the_separator_that_splits_most_is_named_and_works(tmp_path: Path, csv: str) -> None:
    code, said = _import(tmp_path, "mixed.csv", MIXED, "--csv", csv, "--delimiter", "tab")

    assert code == 2, said
    assert "semicolon-separated" in said and "Pass --delimiter ';'" in said
    assert "comma-separated" not in said

    if csv != "auto":  # `auto` finds no narration column here, whatever the delimiter
        code, said = _import(tmp_path, "mixed.csv", MIXED, "--csv", csv, "--delimiter", ";")
        assert code == 0, said
        assert "1 ready" in said


def test_a_delimiter_from_the_mapping_is_advised_in_the_mapping(tmp_path: Path) -> None:
    columns = "date=Date,amount=Amount,narration=Description"
    code, said = _import(tmp_path, "semi.csv", SEMI, "--csv", f"{columns},delimiter=comma")

    assert code == 2, said
    assert "Change delimiter= in --csv to ';', or remove it so bea detects it." in said
    assert "Pass --delimiter" not in said

    code, said = _import(tmp_path, "semi.csv", SEMI, "--csv", f"{columns},delimiter=';'")
    assert code == 0, said
    assert "1 ready" in said
