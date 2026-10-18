"""Output filters protect the whole ledger that includes their input (w5/651)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
ROOT = 'option "title" "Split books"\ninclude "txns/*.bean"\n'
LEAF = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Equity:Opening USD\n"
    '2026-01-02 * "Opening"\n'
    "  Assets:Checking  100.00 USD\n"
    "  Equity:Opening\n"
)


@pytest.mark.parametrize(
    ("command", "destination"),
    [
        (command, destination)
        for command in ("format", "query", "example", "treeify", "ingest")
        for destination in ("txns/copy.bean", "main.bean")
        if (command, destination) != ("example", "main.bean")
    ],
)
def test_output_from_leaf_protects_including_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str, destination: str
) -> None:
    (tmp_path / "txns").mkdir()
    root = tmp_path / "main.bean"
    leaf = tmp_path / "txns/2026.bean"
    root.write_text(ROOT)
    leaf.write_text(LEAF)
    (tmp_path / "ingest.py").write_text("from beangulp import Ingest\nIngest([])()\n")
    monkeypatch.chdir(tmp_path)
    args = {
        "format": ["format", str(leaf)],
        "query": ["--file", str(leaf), "query", "PRINT"],
        "example": ["--file", str(leaf), "example", "--seed", "1"],
        "treeify": ["--file", str(leaf), "treeify"],
        "ingest": ["--file", str(leaf), "ingest", "extract", "input.csv"],
    }[command]

    result = runner.invoke(app, [*args, "-o", destination], input="Assets:Checking  100\n")

    assert result.exit_code == 2, result.output
    assert "would become part" in result.output or "would overwrite the ledger" in result.output
    assert root.read_text() == ROOT
    assert leaf.read_text() == LEAF
    if destination != "main.bean":
        assert not (tmp_path / destination).exists()


def test_leaf_output_can_still_write_outside_the_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "txns").mkdir()
    (tmp_path / "main.bean").write_text(ROOT)
    leaf = tmp_path / "txns/2026.bean"
    leaf.write_text(LEAF)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["format", str(leaf), "-o", "copy.bean"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "copy.bean").read_text() == LEAF


@pytest.mark.parametrize("destination", ["txns/copy.bean", "main.bean"])
def test_stdin_format_protects_working_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, destination: str
) -> None:
    (tmp_path / "txns").mkdir()
    root = tmp_path / "main.bean"
    root.write_text(ROOT)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["format", "-o", destination], input=LEAF)

    assert result.exit_code == 2, result.output
    assert "would become part" in result.output or "would overwrite the ledger" in result.output
    assert root.read_text() == ROOT
    if destination != "main.bean":
        assert not (tmp_path / destination).exists()


@pytest.mark.parametrize("destination", ["main.bean", "txns/copy.bean"])
def test_symlink_leaf_protects_its_named_include_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, destination: str
) -> None:
    books = tmp_path / "books"
    (books / "txns").mkdir(parents=True)
    external = tmp_path / "outside/a/b/c/d/e/leaf.bean"
    external.parent.mkdir(parents=True)
    external.write_text(LEAF)
    (books / "main.bean").write_text(ROOT)
    (books / "txns/leaf.bean").symlink_to(external)
    monkeypatch.chdir(books)

    result = runner.invoke(app, ["format", "txns/leaf.bean", "-o", destination])

    assert result.exit_code == 2, result.output
    assert "would become part" in result.output or "would overwrite the ledger" in result.output
    assert (books / "main.bean").read_text() == ROOT
    assert external.read_text() == LEAF
    if destination != "main.bean":
        assert not (books / destination).exists()


def test_leaf_output_climbs_through_intermediate_includers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    leaf = tmp_path / "a/b/c/d/e/f/leaf.bean"
    leaf.parent.mkdir(parents=True)
    leaf.write_text(LEAF)
    (tmp_path / "a/b/c/section.bean").write_text('include "d/e/f/*.bean"\n')
    root = tmp_path / "main.bean"
    root.write_text('include "a/b/c/section.bean"\n')
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["format", str(leaf), "-o", str(root)])

    assert result.exit_code == 2, result.output
    assert "would overwrite the ledger" in result.output
    assert root.read_text() == 'include "a/b/c/section.bean"\n'
