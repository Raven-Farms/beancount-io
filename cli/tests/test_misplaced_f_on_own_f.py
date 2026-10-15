"""A misplaced `-f LEDGER` after `query` or `ingest archive` is caught (w5/413).

Both define their own `-f`: `query --format`, which named the ledger path an
unknown format with no hint, and Beangulp's `archive --overwrite`, which
replaced documents already filed and archived the ledger as a source, with
exit 0.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.commands import ingest as ingest_command
from cli.main import app

PLACE = "Place -f before the command, for example: bea -f main.bean check."


@pytest.fixture
def books(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n')
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_query_names_the_placement(books: Path) -> None:
    result = CliRunner().invoke(app, ["query", "-f", str(books / "main.bean"), "SELECT 1"])
    assert result.exit_code == 2
    assert f"Unknown query format '{books / 'main.bean'}'" in result.stderr
    assert f"-f after query is --format. {PLACE}" in result.stderr


def test_query_format_still_works(books: Path) -> None:
    result = CliRunner().invoke(app, ["query", "-f", "csv", "SELECT 1"])
    assert "-f after query is --format" not in result.stderr


@pytest.mark.parametrize("flag", ["-f", "--overwrite"])
def test_archive_refuses_a_ledger_after_overwrite(books: Path, monkeypatch: pytest.MonkeyPatch, flag: str) -> None:
    forwarded: list[object] = []
    monkeypatch.setattr(ingest_command, "_forward", lambda *args: forwarded.append(args))

    result = CliRunner().invoke(app, ["ingest", "archive", "-o", "docs", "src", flag, str(books / "main.bean")])

    assert result.exit_code == 2
    assert f"{flag} after ingest archive is Beangulp's --overwrite" in result.stderr
    assert f"{PLACE} Nothing was changed." in result.stderr
    assert forwarded == []


def test_archive_overwrite_alone_still_forwards(books: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    forwarded: list[object] = []
    monkeypatch.setattr(ingest_command, "_forward", lambda *args: forwarded.append(args))
    result = CliRunner().invoke(app, ["ingest", "archive", "-o", "docs", "-f", "src"])
    assert result.exit_code == 0, result.output
    assert len(forwarded) == 1
