"""An explicit `list --limit 50` is told to raise it, not to pass it (w5/836).

The notice compared the value with the default, so `-l 50` typed out was
told "pass --limit for more", the advice w3/325 meant only for a run that
gave none.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    lines = ["2026-01-01 open Assets:Cash USD", "2026-01-01 open Expenses:Food USD"]
    for day in range(80):
        lines += [f'2026-02-{day % 28 + 1:02d} * "T{day}"', "  Expenses:Food  1 USD", "  Assets:Cash"]
    path = tmp_path / "main.bean"
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.mark.parametrize(
    ("limit", "advice"),
    [
        ([], "pass --limit for more"),
        (["-l", "50"], "raise --limit for more"),
        (["--limit=50"], "raise --limit for more"),
    ],
    ids=["default", "short", "long"],
)
def test_the_notice_follows_whether_limit_was_given(ledger: Path, limit: list[str], advice: str) -> None:
    result = runner.invoke(app, ["--file", str(ledger), "list", "transaction", *limit])

    assert result.exit_code == 0, result.output
    assert f"Showing the first 50; {advice}." in result.stderr
