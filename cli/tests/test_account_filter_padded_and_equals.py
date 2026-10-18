"""A padded `--account` matches its account, and `-a=Food` is refused (w5/626).

The blank check tested the stripped value while the raw one was matched, so
`-a " Assets:Cash"` matched nothing with exit 0 in `list` and `balance`.
Click reads `-a=Food` as the value `=Food`, which no account name holds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = """2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Shop" "food"
  Expenses:Food  10.00 USD
  Assets:Cash
2026-01-08 balance Assets:Cash -10.00 USD
"""


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "l.bean"
    path.write_text(LEDGER)
    return path


@pytest.mark.parametrize(
    "args",
    [["list", "balance", "-a", " Assets:Cash"], ["list", "transaction", "-a", "Assets:Cash "]],
    ids=["list-balance", "list-transaction"],
)
def test_a_padded_list_filter_matches(ledger: Path, args: list[str]) -> None:
    result = runner.invoke(app, ["--json", "-f", str(ledger), *args])

    assert result.exit_code == 0, result.output
    assert len(json.loads(result.stdout)["data"]) == 1


def test_a_padded_balance_term_matches(ledger: Path) -> None:
    result = runner.invoke(app, ["-f", str(ledger), "balance", " Assets:Cash"])

    assert result.exit_code == 0, result.output
    assert "-10.00 USD" in result.stdout
    assert "No accounts match" not in result.output


@pytest.mark.parametrize(
    "args",
    [["list", "transaction", "-a=Food"], ["list", "open", "-a=Assets"], ["report", "income-statement", "-a=Expenses"]],
    ids=["list-transaction", "list-open", "report"],
)
def test_an_equals_value_is_refused(ledger: Path, args: list[str]) -> None:
    result = runner.invoke(app, ["-f", str(ledger), *args])

    assert result.exit_code == 2, result.output
    name = args[-1].removeprefix("-a=")
    assert f"Write -a {name} or --account={name}." in " ".join(result.stderr.split())
