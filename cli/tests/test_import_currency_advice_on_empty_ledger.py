"""On a ledger that knows no commodity, the currency advice is one the next run accepts (w5/841).

It advised `--csv currency=CODE`, which the next run refused as "no commodity
this ledger knows". It now leads with opening the source account for one
currency, which is what makes the import read its rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
CSV = ["--csv", "date=Date,amount=Amount,narration=Description", "--account", "Assets:Cash"]


@pytest.mark.parametrize("start", [b"", b"; just a comment\n", b"\xef\xbb\xbf"], ids=["empty", "comment", "bom"])
def test_the_advice_leads_to_an_import_that_reads(tmp_path: Path, start: bytes) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(start)
    (tmp_path / "bank.csv").write_text("Date,Description,Amount\n2026-03-01,Coffee,-3.50\n")
    base = ["--no-input", "--file", str(ledger)]

    first = runner.invoke(app, [*base, "import", str(tmp_path / "bank.csv"), *CSV])

    assert first.exit_code == 2, first.output
    said = " ".join(first.stderr.split())
    assert "the ledger knows no commodity yet. Open Assets:Cash for one currency first" in said
    assert "--csv currency=CODE" not in said
    assert ledger.read_bytes() == start

    opened = runner.invoke(
        app, [*base, "add", "open", "--account", "Assets:Cash", "--currency", "USD", "--date", "2026-01-01"]
    )
    assert opened.exit_code == 0, opened.output
    runner.invoke(app, [*base, "add", "open", "--account", "Expenses:Food", "--date", "2026-01-01"])
    after = runner.invoke(
        app, [*base, "import", str(tmp_path / "bank.csv"), *CSV, "--default-account", "Expenses:Food"]
    )

    assert after.exit_code == 0, after.output
    assert "1 ready" in after.stdout


def test_a_ledger_with_commodities_keeps_its_advice(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text("2026-01-01 commodity USD\n2026-01-01 commodity EUR\n")
    (tmp_path / "bank.csv").write_text("Date,Description,Amount\n2026-03-01,Coffee,-3.50\n")

    result = runner.invoke(app, ["--no-input", "--file", str(ledger), "import", str(tmp_path / "bank.csv"), *CSV])

    assert result.exit_code == 2, result.output
    assert "Name the commodity with --csv currency=CODE" in " ".join(result.stderr.split())


def test_an_already_open_source_is_told_to_declare_a_commodity(tmp_path: Path) -> None:
    """`add open` refuses a second open, so that advice cannot be followed (w5/874)."""
    ledger = tmp_path / "main.bean"
    start = "2024-01-01 open Assets:Cash\n2024-01-01 open Expenses:Uncategorized\n"
    ledger.write_text(start)
    (tmp_path / "bank.csv").write_text("Date,Description,Amount\n2024-02-01,Coffee,-3.50\n")
    base = ["--no-input", "--file", str(ledger)]

    first = runner.invoke(app, [*base, "import", str(tmp_path / "bank.csv"), *CSV])

    assert first.exit_code == 2, first.output
    said = " ".join(first.stderr.split())
    assert "Declare one, then name it with --csv currency=CODE" in said
    assert "add commodity --date YYYY-MM-DD --currency CODE" in said
    assert "Open Assets:Cash" not in said
    assert ledger.read_text() == start

    declared = runner.invoke(app, [*base, "add", "commodity", "--date", "2024-01-01", "--currency", "USD"])
    assert declared.exit_code == 0, declared.output
    named = ["--csv", "date=Date,amount=Amount,narration=Description,currency=USD", "--account", "Assets:Cash"]
    applied = runner.invoke(app, [*base, "import", str(tmp_path / "bank.csv"), "--apply", *named])
    assert applied.exit_code == 0, applied.output
    assert runner.invoke(app, [*base, "check"]).exit_code == 0
