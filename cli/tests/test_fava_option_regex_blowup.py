"""A Fava regex option that cannot compile is ignored, not a report failure (w5/806).

`collapse-pattern` and `insert-entry` values that overflow or recurse at
compile time escaped option parsing and failed every report on a ledger
`bea check` accepts — the recursion case misreported as deep account
nesting. bea ignores these options; uncompilable values are collected like
any other invalid regex.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

NESTED = "(" * 1000 + ")" * 1000

OPTIONS = {
    "overflow": '2000-01-01 custom "fava-option" "collapse-pattern" "Expenses:.{4294967296}"\n',
    "recursion": f'2000-01-01 custom "fava-option" "collapse-pattern" "{NESTED}"\n',
    "insert-overflow": '2000-01-01 custom "fava-option" "insert-entry" "Expenses:.{4294967296}"\n',
    "plain-error": '2000-01-01 custom "fava-option" "collapse-pattern" "(unclosed"\n',
}

COMMANDS = [
    ["balance"],
    ["report", "overview"],
    ["report", "income-statement"],
]

LEDGER = """\
option "operating_currency" "USD"
2024-01-01 open Assets:Checking USD
2024-01-01 open Equity:Opening
2024-01-02 * "x"
  Assets:Checking  5 USD
  Equity:Opening
"""


@pytest.mark.parametrize("option", sorted(OPTIONS), ids=sorted(OPTIONS))
@pytest.mark.parametrize("command", COMMANDS, ids=["balance", "overview", "income-statement"])
def test_uncompilable_option_regex_reports_normally(tmp_path: Path, option: str, command: list[str]) -> None:
    book = tmp_path / "opt.bean"
    book.write_text(OPTIONS[option] + LEDGER)
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0

    result = runner.invoke(app, ["--file", str(book), *command])

    assert result.exit_code == 0, result.output
    assert "too deep" not in " ".join(result.output.split())


def test_uncompilable_option_regex_answers_json(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "opt.bean"
    book.write_text(OPTIONS["overflow"] + LEDGER)

    result = runner.invoke(app, ["--json", "--file", str(book), "report", "income-statement"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert "error" not in payload and "data" in payload
