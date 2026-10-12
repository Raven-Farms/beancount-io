"""An output destination an include glob would claim is refused before it is written (w5/072).

The guard compared a destination with the ledger's files by identity, so a
path that did not exist yet passed — and joined the books on the next load. A
`PRINT` backup saved under `include "txns/*.bean"` doubled every balance with
`check` still exiting 0.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

ROOT = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Equity:Opening USD\n'
JAN = '2026-01-02 * "a"\n  Assets:Cash  5 USD\n  Equity:Opening\n'
BALANCE = "SELECT sum(position) AS total WHERE account = 'Assets:Cash'"


@pytest.fixture
def books(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "books"
    (root / "txns" / "deep").mkdir(parents=True)
    (root / "main.bean").write_text(ROOT + 'include "txns/*.bean"\n')
    (root / "txns" / "jan.bean").write_text(JAN)
    (root / "t.txt").write_text("a\n")
    monkeypatch.chdir(root)
    monkeypatch.delenv("BEA_FILE", raising=False)
    return root


def _files(books: Path) -> set[str]:
    return {str(path.relative_to(books)) for path in books.rglob("*")}


def _command(name: str, destination: str) -> list[str]:
    return {
        "print": ["query", "PRINT FROM date >= 2026-01-02", "-o", destination],
        "csv": ["query", "SELECT date", "-f", "csv", "-o", destination],
        "format": ["format", "main.bean", "-o", destination],
        "treeify": ["treeify", "t.txt", "-o", destination],
        "example": ["example", "-o", destination],
        "example-forced": ["example", "--force", "-o", destination],
    }[name]


@pytest.mark.parametrize("command", ["print", "csv", "format", "treeify", "example", "example-forced"])
def test_a_destination_an_include_glob_matches_is_refused(books: Path, command: str) -> None:
    before = _files(books)

    result = runner.invoke(app, _command(command, "txns/out.bean"))

    assert result.exit_code == 2, result.output
    flat = " ".join(result.output.split())
    assert "would become part of the ledger it reads" in flat
    assert "txns/out.bean" in flat and 'include "txns/*.bean"' in flat
    assert _files(books) == before
    assert runner.invoke(app, ["check"]).exit_code == 0
    assert "5 USD" in runner.invoke(app, ["query", BALANCE]).output


@pytest.mark.parametrize(
    ("include", "holder", "destination"),
    [
        ('include "later.bean"', "main.bean", "later.bean"),
        ('include "txns/**/*.bean"', "main.bean", "txns/deep/out.bean"),
        ('include "txns/**"', "main.bean", "txns/deep/out.txt"),
        ('include "deep/*.bean"', "txns/jan.bean", "txns/deep/out.bean"),
        ('include "{absolute}/txns/deep/*.bean"', "main.bean", "txns/deep/out.bean"),
    ],
    ids=["literal-absent", "recursive", "bare-recursive", "declared-in-child", "absolute-pattern"],
)
def test_every_include_shape_in_the_closure_claims_its_matches(
    books: Path, include: str, holder: str, destination: str
) -> None:
    target = books / holder
    target.write_text(target.read_text() + include.replace("{absolute}", str(books)) + "\n")
    before = _files(books)

    result = runner.invoke(app, ["query", "SELECT date", "-o", destination])

    assert result.exit_code == 2, result.output
    assert "would become part of the ledger it reads" in " ".join(result.output.split())
    assert _files(books) == before


@pytest.mark.parametrize("destination", ["backup.bean", "txns/out.txt", "txns/deep/out.bean", "txns/.hidden.bean"])
def test_a_destination_no_include_matches_is_still_written(books: Path, destination: str) -> None:
    result = runner.invoke(app, ["query", "PRINT FROM date >= 2026-01-02", "-o", destination])

    assert result.exit_code == 0, result.output
    assert "Assets:Cash" in (books / destination).read_text()
    assert runner.invoke(app, ["check"]).exit_code == 0
    assert "5 USD" in runner.invoke(app, ["query", BALANCE]).output


def test_an_existing_member_keeps_its_own_refusal(books: Path) -> None:
    result = runner.invoke(app, ["query", "SELECT date", "-o", "txns/jan.bean"])

    assert result.exit_code == 2, result.output
    assert "would overwrite the ledger it reads" in " ".join(result.output.split())
    assert (books / "txns" / "jan.bean").read_text() == JAN


def test_price_export_refuses_a_directory_the_ledger_includes(books: Path) -> None:
    (books / "archive").mkdir()
    main = books / "main.bean"
    main.write_text(main.read_text() + 'include "archive/*.bean"\n')

    result = runner.invoke(app, ["price", "export", "--allow-errors", "--output", "archive"])

    assert result.exit_code == 2, result.output
    assert "would become part of the ledger being exported" in " ".join(result.output.split())
    assert list((books / "archive").iterdir()) == []
