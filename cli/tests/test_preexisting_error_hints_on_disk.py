"""A refusal for errors already in the ledger describes the ledger as it is (w5/840).

"The ledger already has 1 error(s); nothing was written" carried hints built
from the ledger with the refused write in it: "Did you mean Assets:Bank?",
the account only the refused open names, and "Account opened … at" a line that
was never written.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def _add_open(ledger: Path, account: str, date: str) -> str:
    result = runner.invoke(
        app, ["--file", str(ledger), "add", "open", "--date", date, "--account", account, "--currency", "USD"]
    )
    assert result.exit_code == 1, result.output
    return " ".join(result.stderr.split())


@pytest.mark.parametrize(
    ("text", "account", "date"),
    [
        ("2026-01-01 close Assets:Cash\n", "Assets:Bank", "2026-01-01"),
        ("2026-01-01 close Assets:Cash\n", "Assets:Cash", "2026-02-01"),
        ("2026-01-31 balance Assets:Cash 0 USD\n", "Assets:Bank", "2026-01-01"),
    ],
    ids=["lookalike-close", "open-after-close", "lookalike-balance"],
)
def test_no_hint_comes_from_the_refused_write(tmp_path: Path, text: str, account: str, date: str) -> None:
    ledger = tmp_path / "l.bean"
    ledger.write_text(text)

    said = _add_open(ledger, account, date)

    assert "The ledger already has" in said and "nothing was written" in said
    assert f"Did you mean {account}" not in said
    assert "Account opened" not in said
    assert f"{ledger}:2" not in said and f"{ledger}:3" not in said
    assert ledger.read_text() == text


def test_a_close_of_a_never_opened_account_says_so(tmp_path: Path) -> None:
    ledger = tmp_path / "l.bean"
    ledger.write_text("2026-01-01 close Assets:Cash\n")

    said = _add_open(ledger, "Assets:Bank", "2026-01-01")

    assert "Unopened account Assets:Cash is being closed. The ledger never opens Assets:Cash" in said
