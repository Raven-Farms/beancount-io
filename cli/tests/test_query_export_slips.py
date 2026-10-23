"""Three query export slips (w5/854).

`--spreadsheet-safe` left tag/link cells and header cells starting with `-` or
`=` as they were; an empty `PRINT -o` on a ledger with a validity option wrote
a lone `option` line; and `query -o ''` / `treeify -o ''` called the working
directory a directory instead of naming the empty value.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    'option "operating_currency" "USD"\noption "booking_method" "FIFO"\n'
    "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Shop USD\n"
    '2026-02-01 * "Shop" "x" #-neg ^-lnk\n  Expenses:Shop  12.50 USD\n  Assets:Cash\n'
)


@pytest.fixture
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    return path


def test_spreadsheet_safe_neutralizes_set_cells_and_headers(ledger: Path) -> None:
    query = (
        'SELECT payee, tags, links, joinstr(tags) AS jt, -number, number AS "=HYPERLINK(1)", position '
        "WHERE account ~ 'Expenses'"
    )
    result = runner.invoke(app, ["--file", str(ledger), "query", "-f", "csv", "--spreadsheet-safe", query])

    assert result.exit_code == 0, result.output
    header, row = result.stdout.splitlines()[:2]
    assert header == "payee,tags,links,jt,'-number,'=HYPERLINK(1),position"
    # Numbers and amounts keep their sign.
    assert row == "Shop,'-neg,'-lnk,'-neg,-12.50,12.50,12.50 USD"


def test_an_empty_print_writes_an_empty_file(ledger: Path) -> None:
    result = runner.invoke(app, ["--file", str(ledger), "query", "-o", "y.bean", "PRINT FROM year = 2025"])

    assert result.exit_code == 0, result.output
    assert (ledger.parent / "y.bean").read_bytes() == b""
    assert "option" not in result.stdout


def test_a_print_with_rows_still_carries_the_option_preamble(ledger: Path) -> None:
    result = runner.invoke(app, ["--file", str(ledger), "query", "-o", "y.bean", "PRINT FROM year = 2026"])

    assert result.exit_code == 0, result.output
    assert (ledger.parent / "y.bean").read_text().startswith('option "booking_method" "FIFO"\n')


@pytest.mark.parametrize("command", [["query", "-o", "", "SELECT 1"], ["treeify", "-o", ""]])
def test_an_empty_output_names_the_empty_value(ledger: Path, command: list[str]) -> None:
    result = runner.invoke(app, ["--file", str(ledger), *command], input="")

    assert result.exit_code == 2, result.output
    assert "--output '' is empty; name a path, or omit --output." in result.output
    assert "directory" not in result.output
