"""`list transaction --details` renders the ledger's own strings (w5/834).

It went through the write sanitizer: a TAB became a literal `\\x09` and a line
break a space, so the "Beancount syntax" parsed back as different strings.
A terminal still sees control characters made inert; a redirect gets the text
as the ledger holds it.
"""

from __future__ import annotations

from pathlib import Path

from beancount.parser import parser
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Rent USD\n"
    '2026-01-08 * "Tab\there" "Rent\nfor January"\n  memo: "a\tb"\n  Expenses:Rent  5 USD\n  Assets:Cash\n'
)


def test_the_rendering_parses_back_to_the_ledger_strings(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = runner.invoke(app, ["--file", str(ledger), "list", "transaction", "--details"])

    assert result.exit_code == 0, result.output
    assert "\\x09" not in result.stdout
    rendered = result.stdout.split("\n", 1)[1]  # past the source location line
    entries, errors, _ = parser.parse_string(rendered)
    assert not errors, errors
    (entry,) = entries
    assert (entry.payee, entry.narration, entry.meta["memo"]) == ("Tab\there", "Rent\nfor January", "a\tb")
