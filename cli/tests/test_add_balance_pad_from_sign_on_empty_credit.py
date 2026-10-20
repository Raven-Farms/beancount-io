"""`add balance --pad-from` warns about the sign on a credit-normal account with no history (w5/827).

The negated-balance refusal needs a balance to compare with, so a loan padded
to +5000 USD with no prior history wrote with no warning, and the report then
counted the loan toward net worth; the same assertion without `--pad-from`
flags the sign.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    'option "operating_currency" "USD"\n2026-01-01 open Liabilities:Loan USD\n2026-01-01 open Equity:OpeningBalances\n'
)


def _pad(ledger: Path, amount: str) -> dict[str, object]:
    result = runner.invoke(
        app,
        ["--json", "--file", str(ledger), "add", "balance", "--date", "2026-07-10", "--account", "Liabilities:Loan"]
        + ["--amount", amount, "--pad-from", "Equity:OpeningBalances"],
    )
    assert result.exit_code == 0, result.output
    return dict(json.loads(result.stdout)["data"])


def test_a_positive_pad_on_an_empty_liability_warns(tmp_path: Path) -> None:
    ledger = tmp_path / "z.bean"
    ledger.write_text(LEDGER)

    data = _pad(ledger, "5000 USD")

    warnings = " ".join(data["warnings"])  # type: ignore[arg-type]
    assert (
        "Liabilities balances are negative in Beancount, so an amount owed of 5000 USD is asserted as -5000 USD"
        in warnings
    )


def test_a_negative_pad_says_nothing_about_sign(tmp_path: Path) -> None:
    ledger = tmp_path / "z.bean"
    ledger.write_text(LEDGER)

    data = _pad(ledger, "-5000 USD")

    assert not any("negative in Beancount" in warning for warning in data["warnings"])  # type: ignore[union-attr]


def test_force_help_names_the_sign_override() -> None:
    help_text = " ".join(runner.invoke(app, ["add", "balance", "--help"]).output.split())
    assert "pad to an amount whose sign is refused" in help_text
