"""`list transaction --search` finds a multi-line narration by the text the table shows (w5/631).

The table prints a narration's line breaks as spaces, but the search compared
the raw text, so `Rent for January` matched nothing with exit 0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = """2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Rent USD
2024-01-06 * "Landlord" "Rent
for January"
  Expenses:Rent  1000.00 USD
  Assets:Cash
"""


@pytest.mark.parametrize("term", ["rent for january", "Rent for", "for january", "rent\nfor"])
def test_a_search_matches_across_a_line_break(tmp_path: Path, term: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = runner.invoke(app, ["--json", "--file", str(ledger), "list", "transaction", "--search", term])

    assert result.exit_code == 0, result.output
    (row,) = json.loads(result.stdout)["data"]
    assert row["narration"] == "Rent\nfor January"


def test_the_break_is_one_space_not_none(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = runner.invoke(app, ["--json", "--file", str(ledger), "list", "transaction", "--search", "rentfor"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"] == []
