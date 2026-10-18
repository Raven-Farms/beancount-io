"""`add balance --pad-from` says what it pads, and a statement's sign on a liability is caught (w5/611).

A card statement prints the balance owed as positive; Beancount holds it
negative. Asserting `77.04 USD` against a book of `-77.04 USD` failed with
advice about missing transactions, and with `--pad-from` padded 154.08 USD
with exit 0, the amount never said. A book within tolerance read as an exact
match, and a generated opening command for an owed loan added it to net worth.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CARD = """option "operating_currency" "USD"
2026-07-01 open Liabilities:CreditCard USD
2026-07-01 open Expenses:Dining
2026-07-01 open Equity:OpeningBalances
2026-07-05 * "Dinner"
  Liabilities:CreditCard  -77.04 USD
  Expenses:Dining
"""
BALANCE = ["add", "balance", "--date", "2026-10-02", "--account", "Liabilities:CreditCard"]


def _bea(ledger: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(ledger.parent / "config"),
        XDG_CACHE_HOME=str(ledger.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "--file", str(ledger), *args],
        env=env,
        cwd=ledger.parent,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _ledger(tmp_path: Path, text: str = CARD) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(text)
    return ledger


def _message(result: subprocess.CompletedProcess[str]) -> str:
    return " ".join((result.stdout + result.stderr).split())


SIGN = (
    "Liabilities:CreditCard holds -77.04 USD: Liabilities balances are negative in Beancount, so a statement's "
    "77.04 owed is -77.04 USD. Did you mean -77.04 USD?"
)


def test_the_failed_assertion_names_the_sign(tmp_path: Path) -> None:
    result = _bea(_ledger(tmp_path), *BALANCE, "--amount", "77.04 USD")

    assert result.returncode == 1, result.stderr
    assert SIGN in _message(result)


def test_padding_to_the_negated_balance_needs_force(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    refused = _bea(ledger, *BALANCE, "--amount", "77.04 USD", "--pad-from", "Equity:OpeningBalances")

    assert refused.returncode == 2, refused.stderr
    message = _message(refused)
    assert SIGN in message
    assert "Padding to 77.04 USD would insert 154.08 USD. Pass --force to pad to it anyway." in message
    assert ledger.read_text() == CARD

    forced = _bea(
        ledger, "--json", *BALANCE, "--amount", "77.04 USD", "--pad-from", "Equity:OpeningBalances", "--force"
    )
    assert forced.returncode == 0, forced.stderr
    pad: dict[str, Any] = json.loads(forced.stdout)["data"]["pad"]
    assert pad["amount"] == {"number": "154.08", "currency": "USD"}


def test_the_pad_answer_says_what_it_inserts(tmp_path: Path) -> None:
    result = _bea(_ledger(tmp_path), *BALANCE, "--amount", "-100 USD", "--pad-from", "Equity:OpeningBalances")

    assert result.returncode == 0, result.stderr
    assert "the pad inserts -22.96 USD into Liabilities:CreditCard from Equity:OpeningBalances" in _message(result)


def test_a_book_within_tolerance_is_not_called_a_match(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path,
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Bank USD\n2026-01-01 open Equity:Opening USD\n'
        '2026-01-02 * "x"\n  Assets:Bank  100.004 USD\n  Equity:Opening\n',
    )

    result = _bea(
        ledger, "add", "balance", "--date", "2026-01-05", "-a", "Assets:Bank", "--pad-from", "Equity:Opening",
        "--amount", "100 ~ 0.004 USD",
    )  # fmt: skip

    assert result.returncode == 0, result.stderr
    message = _message(result)
    assert "The book holds 100.004 USD, within the tolerance of the 100 ~ 0.004 USD assertion" in message
    assert "already matches" not in message


def test_an_owed_loan_with_no_history_is_offered_its_negative_sign(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path,
        'option "operating_currency" "USD"\n2026-01-01 open Liabilities:Loan USD\n'
        "2026-01-01 open Equity:OpeningBalances USD\n",
    )

    result = _bea(ledger, "add", "balance", "--date", "2026-01-10", "-a", "Liabilities:Loan", "--amount", "5000 USD")

    assert result.returncode == 1, result.stderr
    message = _message(result)
    assert "an amount owed of 5000 USD is asserted as -5000 USD. Opening adjustment command for that:" in message
    assert "--amount '-5000 USD' --pad-from Equity:OpeningBalances" in message
