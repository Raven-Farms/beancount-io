"""A two-token bulk amount reads the numbers `--posting` reads (w5/213).

`"amount": "1,234.56 USD"` was refused as "not a number" while the flag, and
any bulk amount long enough to reach Beancount's grammar, accepted the same
comma grouping. Acceptance depended on how many tokens the string had.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Broker
2024-01-01 open Assets:Cash USD
"""

# (broker amount, cash amount, broker text written, cash text written)
ACCEPTED = [
    ("1,234.56 USD", "-1,234.56 USD", "1234.56 USD", "-1234.56 USD"),
    ("84/2 USD", "-42 USD", "42 USD", "-42 USD"),
    ("(1+2) USD", "-3 USD", "3 USD", "-3 USD"),
]

# (broker amount, text the refusal must carry)
REFUSED = [
    ("abc USD", "Could not parse amount 'abc USD'"),
    ("1/0 USD", "Division by zero in '1/0 USD'"),
    ("1e3 USD", "Scientific notation '1e3'"),
    ("1_000 USD", "Invalid amount '1_000'"),
]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    return ledger


def _bulk(tmp_path: Path, broker: str, cash: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    ledger = _ledger(tmp_path)
    rows = tmp_path / "rows.json"
    row = {
        "date": "2024-06-01",
        "narration": "deposit",
        "postings": [
            {"account": "Assets:Broker", "amount": broker},
            {"account": "Assets:Cash", "amount": cash},
        ],
    }
    rows.write_text(json.dumps([row]), encoding="utf-8")
    return _bea(tmp_path, "-f", str(ledger), "add", "transactions", "--from", str(rows)), ledger


def _written(ledger: Path) -> list[str]:
    """The posting lines appended after the fixture, whitespace collapsed."""
    added = ledger.read_text(encoding="utf-8")[len(LEDGER) :]
    return [" ".join(line.split()) for line in added.splitlines() if line.startswith("  ")]


@pytest.mark.parametrize(("broker", "cash", "broker_text", "cash_text"), ACCEPTED)
def test_bulk_two_token_amount_goes_through_the_grammar(
    tmp_path: Path, broker: str, cash: str, broker_text: str, cash_text: str
) -> None:
    result, ledger = _bulk(tmp_path, broker, cash)

    assert result.returncode == 0, result.stderr
    assert _written(ledger) == [f"Assets:Broker {broker_text}", f"Assets:Cash {cash_text}"]


@pytest.mark.parametrize(("broker", "cash", "broker_text", "cash_text"), ACCEPTED)
def test_posting_flag_writes_the_same_amounts(
    tmp_path: Path, broker: str, cash: str, broker_text: str, cash_text: str
) -> None:
    """Control: the flag spelling the bulk shorthand is documented to match."""
    ledger = _ledger(tmp_path)

    result = _bea(
        tmp_path,
        *("-f", str(ledger), "add", "transaction", "deposit", "--date", "2024-06-01"),
        *("-p", f"Assets:Broker {broker}", "-p", f"Assets:Cash {cash}"),
    )

    assert result.returncode == 0, result.stderr
    assert _written(ledger) == [f"Assets:Broker {broker_text}", f"Assets:Cash {cash_text}"]


@pytest.mark.parametrize(("broker", "message"), REFUSED)
def test_bulk_two_token_amount_still_refuses_what_the_flag_refuses(tmp_path: Path, broker: str, message: str) -> None:
    result, ledger = _bulk(tmp_path, broker, "-1 USD")

    assert result.returncode == 1
    assert message in " ".join(result.stderr.split())
    assert "Traceback" not in result.stderr
    assert ledger.read_text(encoding="utf-8") == LEDGER


def test_plain_decimal_amount_keeps_its_spelling(tmp_path: Path) -> None:
    """Control: the shortcut for a bare decimal still writes the digits given."""
    result, ledger = _bulk(tmp_path, "12.50 USD", "-12.50 USD")

    assert result.returncode == 0, result.stderr
    assert _written(ledger) == ["Assets:Broker 12.50 USD", "Assets:Cash -12.50 USD"]
