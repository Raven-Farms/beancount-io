"""A subtraction after literal zero must not escape the arithmetic guard (w5/656)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Assets:Brokerage\n"


@pytest.mark.parametrize("divisor", ["0", "-0", "0.0", "+.0"])
@pytest.mark.parametrize("shape", ["transaction", "balance", "cost", "price", "bulk"])
def test_zero_divisor_before_subtraction_is_attributed(tmp_path: Path, divisor: str, shape: str) -> None:
    root = tmp_path / "main.bean"
    root.write_text(LEDGER)
    expression = f"10/{divisor}-5 USD"
    if shape == "balance":
        args = ["add", "balance", "--date", "2026-01-06", "-a", "Assets:Cash", "--amount", expression]
    elif shape == "bulk":
        batch = tmp_path / "batch.json"
        batch.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-01-05",
                        "narration": "Bad amount",
                        "postings": [{"account": "Assets:Cash", "amount": expression}, {"account": "Assets:Brokerage"}],
                    }
                ]
            )
        )
        args = ["add", "transactions", "--from", str(batch)]
    else:
        posting = {
            "transaction": f"Assets:Cash {expression}",
            "cost": f"Assets:Brokerage 1 HOOL {{{expression}}}",
            "price": f"Assets:Brokerage 1 HOOL @ {expression}",
        }[shape]
        other = "Assets:Brokerage" if shape == "transaction" else "Assets:Cash"
        args = ["add", "transaction", "Bad amount", "--date", "2026-01-05", "-p", posting, "-p", other]

    result = runner.invoke(app, ["--json", "--file", str(root), *args])

    assert result.exit_code == (1 if shape == "bulk" else 2), result.output
    assert "Division by zero" in result.output
    assert "SystemError" not in result.output
    assert "Traceback" not in result.output
    assert root.read_text() == LEDGER


def test_nonzero_divisor_with_subtraction_still_writes(tmp_path: Path) -> None:
    root = tmp_path / "main.bean"
    root.write_text(LEDGER)

    result = runner.invoke(
        app,
        [
            "--file",
            str(root),
            "add",
            "transaction",
            "Safe",
            "--date",
            "2026-01-05",
            "-p",
            "Assets:Cash 10/0.5-5 USD",
            "-p",
            "Assets:Brokerage",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "15 USD" in root.read_text()
    checked = runner.invoke(app, ["--json", "--file", str(root), "check"])
    assert checked.exit_code == 0, checked.output
