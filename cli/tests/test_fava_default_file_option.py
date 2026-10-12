"""A ledger carrying Fava's `default-file` option can be reported on (w5/091).

The vendored option setter was a stub raising `NotImplementedError`, which
escaped option parsing: `bea balance` and every `bea report` failed with a
bare exception name on a ledger `bea check` accepts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
option "operating_currency" "USD"

2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening
2026-01-01 open Expenses:Food

2026-01-02 * "Opening balance"
  Assets:Checking  5000.00 USD
  Equity:Opening  -5000.00 USD

2026-07-10 * "Lunch"
  Expenses:Food  12.00 USD
  Assets:Checking
"""
OPTIONS = {
    "bare": '2026-01-02 custom "fava-option" "default-file"\n',
    "with-value": '2026-01-02 custom "fava-option" "default-file" "main.bean"\n',
}
COMMANDS = [
    ["balance"],
    ["report", "overview"],
    ["report", "balance-sheet"],
    ["report", "income-statement"],
    ["report", "trial-balance"],
]


def _data(ledger: Path, *command: str) -> Any:
    result = runner.invoke(app, ["--json", "--file", str(ledger), *command])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


@pytest.mark.parametrize("spelling", sorted(OPTIONS))
@pytest.mark.parametrize("command", COMMANDS, ids=[" ".join(command) for command in COMMANDS])
def test_reports_match_a_copy_without_the_option(
    tmp_path: Path, bea_config_dir: Path, spelling: str, command: list[str]
) -> None:
    plain = tmp_path / "plain" / "main.bean"
    carried = tmp_path / "carried" / "main.bean"
    for path in (plain, carried):
        path.parent.mkdir()
    plain.write_text(LEDGER)
    carried.write_text(LEDGER + OPTIONS[spelling])
    assert runner.invoke(app, ["--file", str(carried), "check"]).exit_code == 0

    with_option = json.dumps(_data(carried, *command)).replace(str(carried.parent), "DIR")
    without = json.dumps(_data(plain, *command)).replace(str(plain.parent), "DIR")

    assert with_option == without


def test_the_text_balance_prints_figures_not_an_exception(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + OPTIONS["bare"])

    result = runner.invoke(app, ["--file", str(ledger), "balance"])

    assert result.exit_code == 0, result.output
    assert "NotImplementedError" not in result.output
    assert "4,988.00 USD" in result.output


def test_the_fiscal_year_option_still_applies(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + OPTIONS["bare"] + '2026-01-01 custom "fava-option" "fiscal-year-end" "06-30"\n')

    data = _data(ledger, "report", "income-statement", "-t", "FY2026")

    assert data["period"] == {"start": "2025-07-01", "end_exclusive": "2026-07-01"}
