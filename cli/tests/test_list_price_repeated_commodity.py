"""The `--amount` hint for a repeated `-c` belongs to `add price` alone (w5/597).

It was attached to any command named `price`, so `bea list price -c HOOL -c
AAPL` was told the quote currency belongs in an `--amount` that `list price`
does not have.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
VALID = Path(__file__).parent / "fixtures" / "valid.bean"
HINT = "the quote currency belongs in --amount"


def test_list_price_gives_the_plain_refusal() -> None:
    result = runner.invoke(app, ["--file", str(VALID), "list", "price", "-c", "HOOL", "-c", "AAPL"])

    assert result.exit_code == 2, result.output
    message = " ".join(result.stderr.split())
    assert "Conflicting values for one option: -c 'HOOL' and -c 'AAPL'. Pass it once." in message
    assert HINT not in message


def test_add_price_keeps_its_hint() -> None:
    result = runner.invoke(app, ["--file", str(VALID), "add", "price", "-c", "HOOL", "-c", "USD", "--amount", "1 USD"])

    assert result.exit_code == 2, result.output
    assert HINT in " ".join(result.stderr.split())
