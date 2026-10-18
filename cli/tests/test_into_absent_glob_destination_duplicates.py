"""A not-yet-existing `--into` file under an include glob keeps duplicate detection (w5/145).

A planned, absent destination sends the whole ledger through the staged
shadow loader even without a managed price include. Counting the planned file,
a one-match glob became two include lines there, so every later line of the
includer was numbered one too high: the price on that line was judged
generated and dropped from the conflict set, and a conflicting quote or an
exact duplicate was written with exit 0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from cli.main import app

runner = CliRunner()

MAIN = """\
option "operating_currency" "USD"
include "2024/*.bean"
2024-01-01 open Assets:Cash USD
2024-01-01 open Assets:Broker
2024-01-01 open Equity:Open
2024-01-01 commodity ACME
2024-03-15 price ACME 10 USD
2024-03-31 balance Assets:Cash 100 USD
"""
PRICE_LINE = 7
BALANCE_LINE = 8
ABSENT = "2024/03.bean"
EXISTING = "2024/02.bean"


def _books(tmp_path: Path) -> Path:
    (tmp_path / "2024").mkdir()
    (tmp_path / "2024" / "01.bean").write_text('2024-01-05 * "open"\n  Assets:Cash  100 USD\n  Equity:Open\n')
    (tmp_path / EXISTING).write_text('2024-02-01 * "zero"\n  Assets:Cash  0 USD\n  Equity:Open\n')
    root = tmp_path / "main.bean"
    root.write_text(MAIN)
    return root


def _price(root: Path, into: str, amount: str, *, as_json: bool = False) -> Result:
    lead = ["--json"] if as_json else []
    add = ["add", "price", "--into", into, "--date", "2024-03-15", "--commodity", "ACME", "--amount", amount]
    return runner.invoke(app, [*lead, "--file", str(root), *add])


def _flat(output: str) -> str:
    return " ".join(output.split())


def _tree(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root.parent)): p.read_text() for p in sorted(root.parent.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("into", [ABSENT, EXISTING], ids=["absent", "existing"])
def test_a_conflicting_quote_is_refused_naming_the_real_line(tmp_path: Path, bea_config_dir: Path, into: str) -> None:
    root = _books(tmp_path)
    before = _tree(root)

    result = _price(root, into, "12 USD")

    assert result.exit_code == 4, result.output
    message = _flat(result.output)
    assert "ACME already has a 2024-03-15 price of 10 USD" in message
    assert f"main.bean:{PRICE_LINE}" in message.replace(" ", "")
    assert "refusing 12 USD" in message
    assert _tree(root) == before
    assert not (tmp_path / ABSENT).exists()


@pytest.mark.parametrize("into", [ABSENT, EXISTING], ids=["absent", "existing"])
def test_an_exact_duplicate_is_reported_at_the_real_line(tmp_path: Path, bea_config_dir: Path, into: str) -> None:
    root = _books(tmp_path)
    before = _tree(root)

    result = _price(root, into, "10 USD", as_json=True)

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    assert data["written"] == 0
    assert data["duplicate"] is True
    assert Path(data["source"]["filename"]).name == "main.bean"
    assert data["source"]["lineno"] == PRICE_LINE
    assert _tree(root) == before


@pytest.mark.parametrize("into", [ABSENT, EXISTING], ids=["absent", "existing"])
def test_a_duplicate_balance_is_reported_at_the_real_line(tmp_path: Path, bea_config_dir: Path, into: str) -> None:
    root = _books(tmp_path)
    before = _tree(root)
    add = ["add", "balance", "--into", into, "--date", "2024-03-31", "--account", "Assets:Cash", "--amount", "100 USD"]

    result = runner.invoke(app, ["--json", "--file", str(root), *add])

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    assert data["written"] == 0
    assert data["duplicate"] is True
    assert data["source"]["lineno"] == BALANCE_LINE
    assert _tree(root) == before


def test_a_quote_for_another_day_still_creates_the_absent_file(tmp_path: Path, bea_config_dir: Path) -> None:
    root = _books(tmp_path)
    add = ["add", "price", "--into", ABSENT, "--date", "2024-03-16", "--commodity", "ACME", "--amount", "11 USD"]

    result = runner.invoke(app, ["--file", str(root), *add])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ABSENT).read_text().split() == ["2024-03-16", "price", "ACME", "11", "USD"]
    assert runner.invoke(app, ["--file", str(root), "check"]).exit_code == 0
