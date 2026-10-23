"""add open --booking no longer offers AVERAGE, which Beancount cannot book (w5/162)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Income:Gains USD
2026-01-02 * "seed"
  Assets:Checking  1000.00 USD
  Income:Gains
"""
BUY_1 = (
    "add",
    "transaction",
    "buy",
    "--date",
    "2026-02-01",
    "-p",
    "Assets:Avg 1 HOOL {10 USD}",
    "-p",
    "Assets:Checking",
)
BUY_2 = (
    "add",
    "transaction",
    "buy",
    "--date",
    "2026-02-02",
    "-p",
    "Assets:Avg 1 HOOL {20 USD}",
    "-p",
    "Assets:Checking",
)
SELL = (
    *("add", "transaction", "sell", "--date", "2026-02-03", "-p", "Assets:Avg -1 HOOL {}"),
    *("-p", "Assets:Checking 15 USD", "-p", "Income:Gains"),
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
        COLUMNS="200",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _open(booking: str) -> tuple[str, ...]:
    return ("add", "open", "--date", "2026-01-01", "--account", "Assets:Avg", "--booking", booking)


def test_help_does_not_offer_average(tmp_path: Path) -> None:
    result = _bea(tmp_path, "add", "open", "--help")
    assert result.returncode == 0, result.stderr
    assert "--booking" in result.stdout
    assert "FIFO" in result.stdout
    assert "AVERAGE" not in result.stdout


@pytest.mark.parametrize("spelling", ["AVERAGE", "average"])
def test_average_is_refused_and_nothing_is_written(tmp_path: Path, spelling: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    result = _bea(tmp_path, *_open(spelling))
    assert result.returncode == 2, result.stderr or result.stdout
    assert "'AVERAGE' is not supported by Beancount" in result.stderr
    assert "Choose one of: STRICT, STRICT_WITH_SIZE, NONE, FIFO, LIFO, HIFO." in result.stderr
    assert ledger.read_text() == LEDGER


def test_average_refusal_in_json(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    result = _bea(tmp_path, "--json", *_open("AVERAGE"))
    assert result.returncode == 2, result.stderr or result.stdout
    assert result.stdout == ""
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert error["exit_code"] == 2
    assert "'AVERAGE' is not supported by Beancount" in error["message"]
    assert ledger.read_text() == LEDGER


def test_unknown_method_choices_omit_average(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    result = _bea(tmp_path, *_open("bogus"))
    assert result.returncode == 2, result.stderr or result.stdout
    assert "Unknown booking method 'BOGUS'" in result.stderr
    assert "AVERAGE" not in result.stderr
    assert ledger.read_text() == LEDGER


def test_fifo_control_opens_buys_and_sells(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    for command in (_open("FIFO"), BUY_1, BUY_2, SELL):
        result = _bea(tmp_path, *command)
        assert result.returncode == 0, result.stderr or result.stdout
    text = ledger.read_text()
    assert '2026-01-01 open Assets:Avg  "FIFO"' in text
    assert "-1 HOOL {}" in text


AVERAGE_LEDGER = LEDGER.replace(
    'option "operating_currency" "USD"\n', 'option "operating_currency" "USD"\noption "booking_method" "AVERAGE"\n'
)


def test_open_inheriting_average_warns_but_writes(tmp_path: Path) -> None:
    """An open without booking inherits the option's AVERAGE, which may never hold lots (w5/764)."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(AVERAGE_LEDGER)
    result = _bea(tmp_path, "add", "open", "--date", "2026-01-01", "--account", "Assets:Avg")
    assert result.returncode == 0, result.stderr
    assert "Assets:Avg inherits booking method AVERAGE" in result.stderr + result.stdout
    assert 'option "booking_method"' in result.stderr + result.stdout
    assert "2026-01-01 open Assets:Avg" in ledger.read_text()


def test_open_inheriting_average_warns_in_json(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(AVERAGE_LEDGER)
    result = _bea(tmp_path, "--json", "add", "open", "--date", "2026-01-01", "--account", "Assets:Avg")
    assert result.returncode == 0, result.stderr
    warnings = json.loads(result.stdout)["data"]["warnings"]
    assert any("inherits booking method AVERAGE" in warning for warning in warnings), warnings


def test_explicit_booking_under_average_option_stays_silent(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(AVERAGE_LEDGER)
    result = _bea(tmp_path, *_open("FIFO"))
    assert result.returncode == 0, result.stderr
    assert "inherits booking method AVERAGE" not in result.stderr + result.stdout


def test_sale_from_an_inheriting_account_names_the_option(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(AVERAGE_LEDGER)
    opened = _bea(tmp_path, "add", "open", "--date", "2026-01-01", "--account", "Assets:Avg")
    assert opened.returncode == 0, opened.stderr
    for command in (BUY_1, BUY_2):
        result = _bea(tmp_path, *command)
        assert result.returncode == 0, result.stderr or result.stdout
    before = ledger.read_text()
    result = _bea(tmp_path, *SELL)
    assert result.returncode == 1, result.stderr or result.stdout
    assert "AVERAGE method is not supported." in result.stderr
    assert "Assets:Avg, which inherits" in result.stderr
    assert 'option "booking_method"' in result.stderr
    assert "or change the option" in result.stderr
    assert ledger.read_text() == before


def test_sale_from_a_hand_written_average_account_names_the_remedy(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + '2026-01-01 open Assets:Avg "AVERAGE"\n')
    for command in (BUY_1, BUY_2):
        result = _bea(tmp_path, *command)
        assert result.returncode == 0, result.stderr or result.stdout
    before = ledger.read_text()
    result = _bea(tmp_path, *SELL)
    assert result.returncode == 1, result.stderr or result.stdout
    assert "AVERAGE method is not supported." in result.stderr
    assert "edit that account's open directive to use FIFO, LIFO, HIFO, STRICT or NONE" in result.stderr
    assert ledger.read_text() == before
