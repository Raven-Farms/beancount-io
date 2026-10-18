"""Wrong cwd-relative --into paths name the root-relative correction (w5/654)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


@pytest.mark.parametrize("from_subdirectory", [False, True])
@pytest.mark.parametrize("operation", ["add", "import"])
@pytest.mark.parametrize("json_output", [False, True])
def test_wrong_into_base_suggests_existing_included_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, from_subdirectory: bool, operation: str, json_output: bool
) -> None:
    books = tmp_path / "ledger"
    (books / "txns").mkdir(parents=True)
    root = books / "main.bean"
    root.write_text(
        'option "operating_currency" "USD"\n'
        "2026-01-01 open Assets:Checking USD\n"
        "2026-01-01 open Expenses:Food USD\n"
        'include "txns/*.bean"\n'
    )
    leaf = books / "txns/2026.bean"
    leaf.write_text("; Existing included file\n")
    source = tmp_path / "statement.csv"
    source.write_text("Date,Description,Amount\n2026-02-01,Lunch,-5.00\n")
    before = {path: path.read_bytes() for path in (root, leaf)}
    monkeypatch.chdir(leaf.parent if from_subdirectory else tmp_path)
    into = "2026.bean" if from_subdirectory else "ledger/txns/2026.bean"
    command = (
        ["add", "transaction", "Lunch", "--date", "2026-02-01", "-p", "Expenses:Food 5 USD", "-p", "Assets:Checking"]
        if operation == "add"
        else [
            "import",
            str(source),
            "--csv",
            "auto",
            "--account",
            "Assets:Checking",
            "--default-account",
            "Expenses:Food",
            "--apply",
        ]
    )
    prefix = [*(["--json"] if json_output else []), "--file", str(root), *command, "--into"]

    result = runner.invoke(app, [*prefix, into])

    assert result.exit_code == 2, result.output
    assert "relative --into" in result.output
    assert str(books) in result.output
    assert "--into txns/2026.bean" in result.output
    assert "Create the directory" not in result.output
    assert "add an include" not in result.output
    assert {path: path.read_bytes() for path in before} == before
    assert {str(path.relative_to(books)) for path in books.rglob("*") if path.is_file()} == {
        "main.bean",
        "txns/2026.bean",
    }

    corrected = runner.invoke(app, [*prefix, "txns/2026.bean"])
    assert corrected.exit_code == 0, corrected.output
    assert '"Lunch"' in leaf.read_text()


def test_cwd_hint_preserves_supplied_symlink_components(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    books = tmp_path / "ledger"
    (books / "txns").mkdir(parents=True)
    (books / "archive").mkdir()
    root = books / "main.bean"
    root.write_text(
        "2026-01-01 open Assets:Checking USD\n"
        "2026-01-01 open Expenses:Food USD\n"
        'include "txns/2026.bean"\ninclude "archive/2026.bean"\n'
    )
    (books / "txns/2026.bean").write_text("; Transactions\n")
    (books / "archive/2026.bean").write_text("; Archive\n")
    (books / "alias").symlink_to(".", target_is_directory=True)
    (books / "txns/alias").symlink_to("../archive", target_is_directory=True)
    monkeypatch.chdir(books / "txns")

    result = runner.invoke(
        app,
        [
            "--file",
            str(root),
            "add",
            "transaction",
            "Lunch",
            "--date",
            "2026-02-01",
            "-p",
            "Expenses:Food 5 USD",
            "-p",
            "Assets:Checking",
            "--into",
            "alias/2026.bean",
        ],
    )

    assert result.exit_code == 2, result.output
    assert "--into archive/2026.bean" in result.output
    assert "--into txns/2026.bean" not in result.output
    assert not (books / "2026.bean").exists()


def test_absolute_into_does_not_get_a_cwd_relative_guess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "txns").mkdir()
    root = tmp_path / "main.bean"
    root.write_text('2026-01-01 open Assets:Checking USD\ninclude "txns/*.bean"\n')
    leaf = tmp_path / "txns/2026.bean"
    leaf.write_text("; Included\n")
    monkeypatch.chdir(leaf.parent)

    result = runner.invoke(
        app,
        [
            "--file",
            str(root),
            "add",
            "note",
            "--date",
            "2026-02-01",
            "-a",
            "Assets:Checking",
            "--comment",
            "Review",
            "--into",
            str(tmp_path / "2026.bean"),
        ],
    )

    assert result.exit_code == 2, result.output
    assert "Did you mean" not in result.output
    assert leaf.read_text() == "; Included\n"
    assert not (tmp_path / "2026.bean").exists()
