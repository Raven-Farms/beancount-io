"""Loading doctor operations report a booking failure as `check` does (w5/859).

Upstream's booking raises on arithmetic it cannot do, and `bean-doctor` loads
with upstream's own loader, so `print-options`, `missing-open`,
`display-context` and `linked` each exited 1 with a bare `DivisionByZero`
traceback where `bea check` names the transaction and its remedy.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
WIDE = "12345678901.123456789012345678"  # 29 significant digits
CASES = {
    "zero-units": (
        '2026-02-01 * "Zero total cost"\n  Assets:Brokerage  0 HOOL {{310 USD}}\n  Assets:Checking  -310 USD\n',
        "Assets:Brokerage holds zero units at a total cost",
    ),
    "too-wide": (
        f'2026-02-01 * "Too wide to infer"\n  Assets:Brokerage  {WIDE} SHIB\n  Assets:Checking\n',
        "wider than the 28 significant digits",
    ),
}
OPENS = "2026-01-01 open Assets:Checking USD\n2026-01-01 open Assets:Brokerage\n\n"


@pytest.mark.parametrize("case", sorted(CASES))
@pytest.mark.parametrize("op", [["print-options"], ["missing-open"], ["display-context"], ["linked", "4"]])
def test_a_loading_operation_names_the_unbookable_transaction(tmp_path: Path, case: str, op: list[str]) -> None:
    text, reason = CASES[case]
    ledger = tmp_path / "main.bean"
    ledger.write_text(OPENS + text)
    before = ledger.read_bytes()

    result = runner.invoke(app, ["doctor", op[0], str(ledger), *op[1:]])

    assert result.exit_code == 1, result.output
    assert f"doctor {op[0]} cannot load {ledger}: {ledger}:4: Beancount cannot book this transaction" in " ".join(
        result.output.split()
    )
    assert reason in " ".join(result.output.split())
    assert "Traceback" not in result.output and "DivisionByZero" not in result.output
    assert ledger.read_bytes() == before


def test_a_valid_ledger_still_answers(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(OPENS + '2026-02-01 * "Buy"\n  Assets:Brokerage  1 HOOL {310 USD}\n  Assets:Checking  -310 USD\n')

    result = runner.invoke(app, ["doctor", "display-context", str(ledger)])

    assert result.exit_code == 0, result.output
    assert "HOOL" in result.output


def test_a_ledger_with_other_errors_is_still_diagnosed(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text('2026-02-01 * "Unopened"\n  Expenses:Food  5 USD\n  Assets:Checking\n')

    result = runner.invoke(app, ["doctor", "missing-open", str(ledger)])

    assert result.exit_code == 0, result.output
    assert "open Expenses:Food" in result.output
