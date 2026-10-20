"""A refused or partial write through an included file says it was checked against the root (w5/828).

The "txns.bean is included by …" note went to the helper's stderr, which the
frontend shows only on success: a refused add, or a `--partial` bulk add with a
bad row, never said which ledger the write was judged against.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
ROOT = '2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food\ninclude "txns.bean"\n'
NOTE = "txns.bean is included by {root}; the write goes to txns.bean and is checked against that whole ledger."


@pytest.fixture
def leaf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.bean").write_text(ROOT)
    path = tmp_path / "txns.bean"
    path.write_text("; transactions\n")
    return path


def test_a_refused_add_names_the_root(leaf: Path) -> None:
    result = runner.invoke(
        app,
        ["--no-input", "--file", str(leaf), "add", "transaction", "--date", "2026-01-03", "b"]
        + ["-p", "Expenses:Nope 2 USD", "-p", "Assets:Cash"],
    )

    assert result.exit_code == 1, result.output
    assert NOTE.format(root=leaf.parent / "main.bean") in " ".join(result.stderr.split())
    assert leaf.read_text() == "; transactions\n"


def test_a_partial_bulk_add_carries_the_note_in_json(leaf: Path) -> None:
    rows = [
        {
            "date": "2026-01-04",
            "narration": "ok",
            "postings": [{"account": "Expenses:Food", "amount": "1 USD"}, {"account": "Assets:Cash"}],
        },
        {
            "date": "2026-01-05",
            "narration": "bad",
            "postings": [{"account": "Expenses:Nope", "amount": "1 USD"}, {"account": "Assets:Cash"}],
        },
    ]
    batch = leaf.parent / "b.json"
    batch.write_text(json.dumps(rows))

    result = runner.invoke(
        app, ["--json", "--no-input", "--file", str(leaf), "add", "transactions", "--from", str(batch), "--partial"]
    )

    assert result.exit_code == 1, result.output
    error = json.loads(result.stderr)["error"]
    note = NOTE.format(root=leaf.parent / "main.bean")
    assert error["result"]["written"] == 1
    assert note in error["result"]["warnings"] and note in error["details"]
