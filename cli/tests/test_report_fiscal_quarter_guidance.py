"""Fiscal-quarter refusals name the right year and declaration, and no refused period is suggested (w5/808).

The refusal always suggested "FY2027", cited the first `fiscal-year-end`
declaration although Fava keeps the last valid one, and refused a period
when an earlier declaration was invalid even though a later valid one was
in effect. `balance FY2026-Q1` on a year without quarters suggested
`-t FY2026-Q1`, which was then refused.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
HEAD = 'option "operating_currency" "USD"\n2020-01-01 open Assets:Checking USD\n2020-01-01 open Expenses:Food USD\n'
SPEND = '2026-05-01 * "lunch"\n  Expenses:Food  3.00 USD\n  Assets:Checking\n'


def _ledger(tmp_path: Path, *values: str) -> Path:
    declarations = "".join(f'2020-01-01 custom "fava-option" "fiscal-year-end" "{value}"\n' for value in values)
    ledger = tmp_path / "main.bean"
    ledger.write_text(HEAD + declarations + SPEND)
    return ledger


def _json(ledger: Path, *args: str) -> tuple[int, Any]:
    result = runner.invoke(app, ["--json", "--file", str(ledger), *args])
    return result.exit_code, json.loads(result.stdout if result.exit_code == 0 else result.stderr)


def test_the_refusal_suggests_the_year_that_holds_the_quarter(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, "04-05")

    for year in ("2020", "2031"):
        exit_code, payload = _json(ledger, "report", "income-statement", "-t", f"FY{year}-Q3")

        assert exit_code == 2, payload
        assert payload["error"]["details"] == [
            f"Report the whole fiscal year (FY{year}), or name the months by calendar dates."
        ]


def test_the_refusal_cites_the_declaration_in_effect(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, "03-31", "04-05")

    exit_code, payload = _json(ledger, "report", "income-statement", "-t", "FY2026-Q1")

    assert exit_code == 2, payload
    assert f'"fiscal-year-end" at {ledger}:5)' in payload["error"]["message"]


def test_a_later_valid_declaration_is_in_effect(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, "06-31", "03-31")

    exit_code, payload = _json(ledger, "report", "income-statement", "-t", "FY2026")

    assert exit_code == 0, payload
    assert payload["data"]["period"] == {"start": "2025-04-01", "end_exclusive": "2026-04-01"}


def test_a_later_invalid_declaration_is_still_refused(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, "03-31", "06-31")

    exit_code, payload = _json(ledger, "report", "income-statement", "-t", "FY2026")

    assert exit_code == 1, payload
    assert "fiscal-year-end option is invalid" in payload["error"]["message"]


def test_no_hint_suggests_a_quarter_the_year_does_not_have(tmp_path: Path) -> None:
    no_quarters = _ledger(tmp_path, "04-05")
    result = runner.invoke(app, ["--file", str(no_quarters), "balance", "FY2026-Q1"])
    assert result.exit_code == 0, result.output
    assert "pass -t" not in result.output

    (tmp_path / "q").mkdir()
    quarters = _ledger(tmp_path / "q", "03-31")
    control = runner.invoke(app, ["--file", str(quarters), "balance", "FY2026-Q1"])
    assert control.exit_code == 0, control.output
    assert "For the period FY2026-Q1, pass -t FY2026-Q1." in " ".join(control.output.split())
