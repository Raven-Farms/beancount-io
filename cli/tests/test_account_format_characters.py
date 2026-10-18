"""Format characters stay visible in refusals and cannot create new lookalike accounts (w5/657)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
FORMATS = ["\u200b", "\u2060", "\ufeff", "\u00ad", "\u200c", "\u200d"]
LEDGER = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n"


@pytest.mark.parametrize("character", FORMATS, ids=lambda c: f"U+{ord(c):04X}")
@pytest.mark.parametrize("operation", ["transaction", "balance", "bulk"])
@pytest.mark.parametrize("json_output", [False, True])
def test_unknown_account_diagnostics_and_new_open_do_not_hide_formats(
    tmp_path: Path, character: str, operation: str, json_output: bool
) -> None:
    root = tmp_path / "main.bean"
    root.write_text(LEDGER)
    account = f"Expenses:Food{character}"
    if operation == "transaction":
        args = ["add", "transaction", "Lunch", "--date", "2026-01-05", "-p", f"{account} 5 USD", "-p", "Assets:Cash"]
    elif operation == "balance":
        args = ["add", "balance", "--date", "2026-01-06", "-a", account, "--amount", "5 USD"]
    else:
        batch = tmp_path / "batch.json"
        batch.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-01-05",
                        "narration": "Lunch",
                        "postings": [{"account": account, "amount": "5 USD"}, {"account": "Assets:Cash"}],
                    }
                ]
            )
        )
        args = ["add", "transactions", "--from", str(batch)]

    prefix = [*(["--json"] if json_output else []), "--file", str(root)]
    refused = runner.invoke(app, [*prefix, *args])

    assert refused.exit_code == 1, refused.output
    diagnostic = json.dumps(json.loads(refused.stderr)["error"], ensure_ascii=False) if json_output else refused.output
    assert character not in diagnostic
    assert ascii(character)[1:-1] in diagnostic
    assert f"U+{ord(character):04X}" in diagnostic
    assert "add open --account" not in diagnostic
    assert root.read_text() == LEDGER

    opened = runner.invoke(app, [*prefix, "add", "open", "--date", "2026-01-01", "-a", account])
    assert opened.exit_code == 2, opened.output
    diagnostic = json.dumps(json.loads(opened.stderr)["error"], ensure_ascii=False) if json_output else opened.output
    assert f"U+{ord(character):04X}" in diagnostic
    assert character not in diagnostic
    assert root.read_text() == LEDGER


@pytest.mark.parametrize("character", FORMATS, ids=lambda c: f"U+{ord(c):04X}")
def test_an_existing_account_with_a_format_character_remains_usable(tmp_path: Path, character: str) -> None:
    root = tmp_path / "main.bean"
    account = f"Expenses:Food{character}"
    root.write_text(LEDGER + f"2026-01-01 open {account} USD\n")

    added = runner.invoke(
        app,
        [
            "--file",
            str(root),
            "add",
            "transaction",
            "Lunch",
            "--date",
            "2026-01-05",
            "-p",
            f"{account} 5 USD",
            "-p",
            "Assets:Cash",
        ],
    )

    assert added.exit_code == 0, added.output
    assert f"  {account}  5 USD" in root.read_text()
    balanced = runner.invoke(
        app, ["--file", str(root), "add", "balance", "--date", "2026-01-06", "-a", account, "--amount", "5 USD"]
    )
    assert balanced.exit_code == 0, balanced.output
    checked = runner.invoke(app, ["--json", "--file", str(root), "check"])
    assert checked.exit_code == 0, checked.output


@pytest.mark.parametrize("character", ["\u200b", "\u200c"], ids=lambda c: f"U+{ord(c):04X}")
@pytest.mark.parametrize("existing", [False, True])
def test_import_never_proposes_an_uncreatable_format_name(tmp_path: Path, character: str, existing: bool) -> None:
    root = tmp_path / "main.bean"
    account = f"Expenses:Food{character}"
    original = LEDGER + (f"2026-01-01 open {account} USD\n" if existing else "")
    root.write_text(original)
    source = tmp_path / "bank.csv"
    source.write_text("Date,Description,Amount\n2026-01-05,Lunch,-5.00\n")

    result = runner.invoke(
        app,
        [
            "--json",
            "--file",
            str(root),
            "import",
            str(source),
            "--csv",
            "auto",
            "--account",
            "Assets:Cash",
            "--default-account",
            account,
            *(["--apply"] if existing else []),
        ],
    )

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    if existing:
        assert data["written"] == 1
        assert f"  {account}  " in root.read_text()
    else:
        assert data["blocked"] == 1
        reason = data["rows"][0]["reason"]
        assert character not in reason
        assert f"U+{ord(character):04X}" in reason
        assert "add open" not in reason
        assert root.read_text() == original
