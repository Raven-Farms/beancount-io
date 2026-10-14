"""Two different values for one single-valued `add` option are refused (w5/238).

`--commodity` and `--currency` are one option on `add price`, so passing both
recorded a price for the quote currency itself; `-a One -a Two` opened only the
last account. Each exited 0 after silently dropping a value.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2024-01-01 open Assets:Checking USD
2024-01-01 open Assets:Broker HOOL
2024-01-01 open Expenses:Food USD
2024-01-01 open Equity:Opening USD
2024-01-01 commodity HOOL
2024-01-02 * "Opening"
  Assets:Checking  1000.00 USD
  Equity:Opening
"""
DATE = ("--date", "2024-06-01")
POSTINGS = ("-p", "Expenses:Food 1 USD", "-p", "Assets:Checking")


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", "main.bean", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (
            ["add", "price", *DATE, "--commodity", "HOOL", "--currency", "USD", "--amount", "130 USD"],
            ["--commodity 'HOOL'", "--currency 'USD'", "quote currency belongs in --amount"],
        ),
        (["add", "open", *DATE, "-a", "Assets:One", "-a", "Assets:Two"], ["-a 'Assets:One'", "-a 'Assets:Two'"]),
        (
            ["add", "note", *DATE, "-a", "Assets:Checking", "--comment", "first", "--message", "second"],
            ["--comment 'first'", "--message 'second'"],
        ),
        (["add", "commodity", *DATE, "--commodity", "AAA", "-c", "BBB"], ["--commodity 'AAA'", "-c 'BBB'"]),
        (
            ["add", "close", *DATE, "--account=Assets:Checking", "-aAssets:Broker"],
            ["--account 'Assets:Checking'", "-a 'Assets:Broker'"],
        ),
        (
            ["add", "transaction", "Coffee", *DATE, "--date", "2024-06-02", *POSTINGS],
            ["--date '2024-06-01'", "--date '2024-06-02'"],
        ),
        (
            ["add", "transaction", "Coffee", *DATE, *POSTINGS, "--into", "a.bean", "--into", "b.bean"],
            ["--into 'a.bean'", "--into 'b.bean'"],
        ),
    ],
    ids=["price-alias", "open-account", "note-alias", "commodity-alias", "close-attached", "txn-date", "into"],
)
def test_conflicting_values_exit_2_and_write_nothing(tmp_path: Path, args: list[str], named: list[str]) -> None:
    result = _bea(tmp_path, *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert "Conflicting values for one option" in result.stderr
    for text in named:
        assert text in result.stderr
    assert "Traceback" not in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_json_conflict_is_a_usage_error_envelope(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json", "add", "event", *DATE, "-t", "location", "-t", "employer", "-d", "Paris")

    assert result.returncode == 2, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert "-t 'location' and -t 'employer'" in error["message"]
    assert (tmp_path / "main.bean").read_text() == LEDGER


@pytest.mark.parametrize(
    ("args", "appended"),
    [
        (["add", "price", *DATE, "--commodity", "HOOL", "--amount", "130 USD"], "2024-06-01 price HOOL"),
        # The same value twice is a retried flag, not a contradiction.
        (
            ["add", "note", *DATE, "-a", "Assets:Checking", "--comment", "same", "-m", "same"],
            '2024-06-01 note Assets:Checking "same"',
        ),
        # Options documented as repeatable still collect every value.
        (["add", "open", *DATE, "-a", "Assets:One", "-c", "USD", "-c", "EUR"], "2024-06-01 open Assets:One USD,EUR"),
    ],
    ids=["single-value", "same-value-twice", "repeatable-option"],
)
def test_controls_still_write(tmp_path: Path, args: list[str], appended: str) -> None:
    result = _bea(tmp_path, *args)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Added 1 " in result.stdout
    assert appended in (tmp_path / "main.bean").read_text()[len(LEDGER) :]
