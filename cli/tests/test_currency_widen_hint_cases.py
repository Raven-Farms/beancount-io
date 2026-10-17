"""The w5/363 currency hint keeps the booking, prices filled-in legs, and merges a duplicate open (w5/488).

The suggested `open` dropped `"FIFO"`; a card leg Beancount filled in was told
to widen the card's currencies instead of pricing the meal; and a second
`add open` produced `USD,USD` from the existing postings' side-effect error.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = """option "operating_currency" "USD"
2026-01-01 open Expenses:Dining
2026-01-01 open Liabilities:CreditCard USD
"""
CHECKING = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "Opening"
  Assets:Checking  1000 USD
  Equity:Opening
"""


def _bea(tmp_path: Path, ledger: str, *args: str) -> str:
    (tmp_path / "main.bean").write_text(ledger)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert (tmp_path / "main.bean").read_text() == ledger
    return " ".join(result.stderr.split())


def test_the_suggested_open_keeps_its_booking(tmp_path: Path) -> None:
    ledger = (
        'option "operating_currency" "USD"\n'
        '2026-01-01 open Assets:Broker USD "FIFO"\n  institution: "Acme"\n2026-01-01 open Assets:Cash USD\n'
    )
    text = _bea(
        tmp_path,
        ledger,
        "add",
        "transaction",
        "Buy",
        "--date",
        "2026-01-05",
        "-p",
        "Assets:Broker 2 HOOL {10 USD}",
        "-p",
        "Assets:Cash",
    )

    assert "edit that open to '2026-01-01 open Assets:Broker USD,HOOL \"FIFO\"'" in text


def test_a_filled_in_leg_is_told_to_price_the_other(tmp_path: Path) -> None:
    text = _bea(
        tmp_path,
        CARD,
        "add",
        "transaction",
        "Dinner",
        "--date",
        "2026-01-05",
        "-p",
        "Expenses:Dining 45 EUR",
        "-p",
        "Liabilities:CreditCard",
    )

    assert "Liabilities:CreditCard was given no amount, so Beancount filled in EUR from the other legs." in text
    assert "price the EUR leg at the rate paid: 'Expenses:Dining 45 EUR @ RATE USD'" in text
    assert "edit that open" not in text


def test_an_explicit_leg_still_gets_the_widen_hint(tmp_path: Path) -> None:
    text = _bea(
        tmp_path,
        CARD,
        "add",
        "transaction",
        "Dinner",
        "--date",
        "2026-01-05",
        "-p",
        "Expenses:Dining 45 EUR",
        "-p",
        "Liabilities:CreditCard -45 EUR",
    )

    assert "edit that open to '2026-01-01 open Liabilities:CreditCard USD,EUR'" in text


def test_a_duplicate_open_names_the_merged_list(tmp_path: Path) -> None:
    text = _bea(tmp_path, CHECKING, "add", "open", "--date", "2026-08-01", "--account", "Assets:Checking", "-c", "EUR")

    assert "Duplicate open directive for Assets:Checking" in text
    assert (
        "an account opens once. To allow EUR too, edit that open to '2026-01-01 open Assets:Checking USD,EUR'" in text
    )
    assert "This follows from the duplicate open of Assets:Checking above." in text
    assert "USD,USD" not in text
