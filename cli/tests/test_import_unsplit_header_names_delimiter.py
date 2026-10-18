"""A forced `--delimiter` that does not split the header is named, on every path (w5/622).

w3/226 named the delimiter only for `--csv auto` and only for `;`, tab and
`|` in the header. An explicit mapping was told `Date` was missing, and a
forced `;` on a comma file got a mapping to paste that failed the same way.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
MAPPING = "date=Date,amount=Amount,narration=Description"


@pytest.mark.parametrize(
    ("body", "options", "looks", "advice"),
    [
        (
            "Date;Description;Amount\n2026-04-01;Coffee shop;-4.50\n",
            ["--csv", MAPPING, "--delimiter", ","],
            "semicolon",
            "';'",
        ),
        (
            "Date,Description,Amount\n2026-04-01,Coffee shop,-4.50\n",
            ["--csv", "auto", "--delimiter", ";"],
            "comma",
            "','",
        ),
    ],
    ids=["explicit-mapping", "comma-file-under-semicolon"],
)
def test_the_refusal_names_the_delimiter_and_suggests_no_mapping(
    tmp_path: Path, bea_config_dir: Path, body: str, options: list[str], looks: str, advice: str
) -> None:
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n'
        "2026-01-01 open Expenses:Uncategorized USD\n"
    )
    (tmp_path / "export.csv").write_text(body)

    result = runner.invoke(
        app,
        ["--no-input", "-f", str(tmp_path / "main.bean"), "import", str(tmp_path / "export.csv")]
        + [*options, "--account", "Assets:Checking"],
    )

    assert result.exit_code == 2, result.output
    message = " ".join(result.stderr.split())
    assert "one column" in message
    assert f"looks {looks}-separated" in message
    assert f"Pass --delimiter {advice}" in message
    assert "lacks" not in message
    assert "Name them with --csv" not in message
