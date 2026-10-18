"""Explain unique_prices conflicts from implied quotes as well as price directives (w5/665)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from tests.test_price import _run_bea, _write_managed_ledger
from tests.test_price import feed_server as feed_server

runner = CliRunner()
HEADER = (
    'option "operating_currency" "USD"\n'
    'plugin "beancount.plugins.implicit_prices"\n'
    'plugin "beancount.plugins.unique_prices"\n'
    "2026-01-01 open Assets:Cash USD\n"
    "2026-01-01 open Assets:Euro EUR\n"
)
TRADE = '2026-01-05 * "FX"\n  Assets:Euro 100 EUR @ 1.08 USD\n  Assets:Cash -108 USD\n'


@pytest.mark.parametrize("operation", ["transaction", "cost-transaction", "price", "price-force"])
@pytest.mark.parametrize("split", [False, True])
@pytest.mark.parametrize("json_output", [False, True])
def test_conflicts_name_each_quote_and_its_written_or_proposed_origin(
    tmp_path: Path, operation: str, split: bool, json_output: bool
) -> None:
    root = tmp_path / "main.bean"
    existing = tmp_path / "trades.bean" if split else root
    if split:
        root.write_text(HEADER + 'include "trades.bean"\n')
        existing.write_text(TRADE)
    else:
        root.write_text(HEADER + TRADE)
    before = {path: path.read_bytes() for path in tmp_path.glob("*.bean")}
    if operation.startswith("price"):
        quote = "1.10"
        command = ["add", "price", "--date", "2026-01-05", "--currency", "EUR", "--amount", f"{quote} USD"]
        if operation == "price-force":
            command.append("--force")
        origin = "proposed price (not written)"
    else:
        quote = "1.09"
        leg = "Assets:Euro 10 EUR {1.09 USD}" if operation == "cost-transaction" else "Assets:Euro 10 EUR @ 1.09 USD"
        command = ["add", "transaction", "FX2", "--date", "2026-01-05", "-p", leg, "-p", "Assets:Cash -10.90 USD"]
        origin = "implied by the proposed transaction (not written)"

    result = runner.invoke(app, [*(["--json"] if json_output else []), "--file", str(root), *command])

    assert result.exit_code == 1, result.output
    details = (
        " ".join(json.loads(result.stderr)["error"]["details"]) if json_output else " ".join(result.output.split())
    )
    assert "unique_prices plugin permits one rate per date and currency pair" in details
    line = 1 if split else 6
    assert f"1.08 USD per EUR on 2026-01-05, implied by the transaction at {existing}:{line}" in details
    assert f"{quote} USD per EUR on 2026-01-05, {origin}" in details
    assert "--force cannot bypass this validation" in details
    assert ".bea-" not in details
    assert {path: path.read_bytes() for path in tmp_path.glob("*.bean")} == before


@pytest.mark.parametrize("operation", ["transaction", "price"])
def test_an_agreeing_implied_or_written_quote_remains_valid(tmp_path: Path, operation: str) -> None:
    root = tmp_path / "main.bean"
    root.write_text(HEADER + TRADE)
    if operation == "price":
        command = ["add", "price", "--date", "2026-01-05", "--currency", "EUR", "--amount", "1.08 USD"]
    else:
        command = [
            "add", "transaction", "FX2", "--date", "2026-01-05",
            "-p", "Assets:Euro 10 EUR @ 1.08 USD", "-p", "Assets:Cash -10.80 USD",
        ]  # fmt: skip

    result = runner.invoke(app, ["--file", str(root), *command])

    assert result.exit_code == 0, result.output
    assert runner.invoke(app, ["--file", str(root), "check"]).exit_code == 0


@pytest.mark.parametrize("json_output", [False, True])
def test_an_existing_written_price_is_named_as_written_in_transaction_refusals(
    tmp_path: Path, json_output: bool
) -> None:
    root = tmp_path / "main.bean"
    original = HEADER + "2026-01-05 price EUR 1.08 USD\n"
    root.write_text(original)

    result = runner.invoke(
        app,
        [
            *(["--json"] if json_output else []), "--file", str(root), "add", "transaction", "FX2",
            "--date", "2026-01-05", "-p", "Assets:Euro 10 EUR @ 1.09 USD", "-p", "Assets:Cash -10.90 USD",
        ],
    )  # fmt: skip

    assert result.exit_code == 1, result.output
    details = (
        " ".join(json.loads(result.stderr)["error"]["details"]) if json_output else " ".join(result.output.split())
    )
    assert f"1.08 USD per EUR on 2026-01-05, written price at {root}:6" in details
    assert "1.09 USD per EUR on 2026-01-05, implied by the proposed transaction (not written)" in details
    assert root.read_text() == original


@pytest.mark.parametrize("json_output", [False, True])
def test_an_existing_managed_feed_quote_is_never_called_a_proposal(
    tmp_path: Path, feed_server: str, json_output: bool
) -> None:
    root = _write_managed_ledger(
        tmp_path,
        feed_server,
        'plugin "beancount.plugins.implicit_prices"\nplugin "beancount.plugins.unique_prices"\n',
    )
    before = root.read_bytes()

    result = _run_bea(
        tmp_path, feed_server, *(["--json"] if json_output else []), "--file", str(root),
        "add", "transaction", "Buy", "--date", "2026-09-10",
        "-p", "Assets:Broker 1 BTC @ 113000 USD", "-p", "Expenses:Food -113000 USD",
    )  # fmt: skip

    assert result.returncode == 1, result.stdout + result.stderr
    details = (
        " ".join(json.loads(result.stderr)["error"]["details"]) if json_output else " ".join(result.stderr.split())
    )
    assert f"112000.00 USD per BTC on 2026-09-10, managed price from {feed_server}/prices/BTC-USD" in details
    assert "113000 USD per BTC on 2026-09-10, implied by the proposed transaction (not written)" in details
    assert "112000.00 USD per BTC on 2026-09-10, proposed" not in details
    assert ".bea-" not in details
    assert root.read_bytes() == before
