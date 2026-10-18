"""An earlier-dated proposal never becomes the existing open in the remedy (w5/658)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    'option "operating_currency" "USD"\n'
    '2026-01-01 open Assets:Checking USD "FIFO"\n'
    "2026-01-01 open Equity:OpeningBalances USD\n\n"
    '2026-01-02 * "Opening"\n'
    "  Assets:Checking 500 USD\n"
    "  Equity:OpeningBalances\n"
)


@pytest.mark.parametrize("date", ["2025-12-01", "2026-01-01", "2026-02-01"])
@pytest.mark.parametrize("layout", ["single", "existing-in-include", "append-to-include"])
@pytest.mark.parametrize("json_output", [False, True])
def test_duplicate_open_remedy_names_the_persisted_open(
    tmp_path: Path, date: str, layout: str, json_output: bool
) -> None:
    root = tmp_path / "main.bean"
    existing = root
    into: list[str] = []
    if layout == "existing-in-include":
        existing = tmp_path / "accounts.bean"
        existing.write_text(LEDGER)
        root.write_text('include "accounts.bean"\n')
    elif layout == "append-to-include":
        root.write_text(LEDGER + 'include "extra.bean"\n')
        (tmp_path / "extra.bean").write_text("; New directives go here\n")
        into = ["--into", "extra.bean"]
    else:
        root.write_text(LEDGER)
    before = {path: path.read_bytes() for path in tmp_path.glob("*.bean")}

    result = runner.invoke(
        app,
        [
            *(["--json"] if json_output else []),
            "--file",
            str(root),
            "add",
            "open",
            "--date",
            date,
            "--account",
            "Assets:Checking",
            "-c",
            "EUR",
            *into,
        ],
    )

    assert result.exit_code == 1, result.output
    diagnostic = json.dumps(json.loads(result.stderr)["error"]) if json_output else result.output
    text = " ".join(diagnostic.split()).replace('\\"', '"')
    assert f"Assets:Checking is already opened at {existing}:2 for USD;" in text
    assert "edit that open to '2026-01-01 open Assets:Checking USD,EUR \"FIFO\"'" in text
    assert "EUR,USD" not in text
    assert ".bea-" not in text
    assert {path: path.read_bytes() for path in tmp_path.glob("*.bean")} == before


@pytest.mark.parametrize("date", ["2025-12-01", "2026-02-01"])
@pytest.mark.parametrize("json_output", [False, True])
def test_new_duplicate_currency_is_kept_when_the_ledger_already_has_duplicates(
    tmp_path: Path, date: str, json_output: bool
) -> None:
    root = tmp_path / "main.bean"
    original = "2026-01-01 open Assets:Cash USD\n2026-01-02 open Assets:Cash EUR\n"
    root.write_text(original)

    result = runner.invoke(
        app,
        [
            *(["--json"] if json_output else []),
            "--file",
            str(root),
            "add",
            "open",
            "--date",
            date,
            "--account",
            "Assets:Cash",
            "-c",
            "GBP",
            "--allow-errors",
        ],
    )

    assert result.exit_code == 1, result.output
    diagnostic = json.dumps(json.loads(result.stderr)["error"]) if json_output else result.output
    text = " ".join(diagnostic.split())
    assert f"Assets:Cash is already opened at {root}:1 for USD;" in text
    assert "edit that open to '2026-01-01 open Assets:Cash USD,GBP'" in text
    assert root.read_text() == original
