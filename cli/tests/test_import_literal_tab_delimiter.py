"""A literal tab is accepted as an import delimiter (w5/621).

`parse_delimiter` accepted `"\\t"` but stripped its input first, which
deleted the tab: `--delimiter $'\\t'`, the usual shell spelling for TSV, was
refused, and `--csv …,delimiter=<TAB>` fell into the "bare comma" message,
which then listed "a literal tab" as accepted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
MAPPING = "date=Date,amount=Amount,narration=Description"


@pytest.mark.parametrize(
    "options",
    [
        ["--csv", MAPPING, "--delimiter", "\t"],
        ["--csv", f"{MAPPING},delimiter=\t"],
        ["--csv", f"{MAPPING},delimiter='\t'"],
    ],
    ids=["flag", "spec", "quoted-spec"],
)
def test_a_tab_separated_export_imports(tmp_path: Path, bea_config_dir: Path, options: list[str]) -> None:
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n'
        "2026-01-01 open Expenses:Uncategorized USD\n"
    )
    (tmp_path / "t.csv").write_text("Date\tDescription\tAmount\n2026-04-01\tCoffee shop\t-4.50\n")

    result = runner.invoke(
        app,
        ["--json", "--no-input", "-f", str(tmp_path / "main.bean"), "import", str(tmp_path / "t.csv")]
        + [*options, "--account", "Assets:Checking"],
    )

    assert result.exit_code == 0, result.output
    (row,) = json.loads(result.stdout)["data"]["rows"]
    assert row["narration"] == "Coffee shop" and row["amount"] == "-4.50 USD"
