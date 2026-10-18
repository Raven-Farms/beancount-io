"""An explicit bad pad date needs a pad-date remedy, while derived-date advice stays useful (w5/688)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Equity:Opening-Balances USD
2024-01-01 open Assets:Cash USD
2024-06-01 open Expenses:Travel USD
"""
EXPLICIT_HINT = (
    "The pad date {pad_date} is before Expenses:Travel opens (2024-06-01); "
    "pass --pad-date 2024-06-01 or later, with a balance --date later than the pad date."
)


def _bea(ledger: Path, *args: str, as_json: bool = False) -> subprocess.CompletedProcess[str]:
    directory = ledger.parent
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if as_json else []), "--file", str(ledger), *args],
        env=env,
        cwd=directory,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _balance(date: str, *, pad_date: str | None = None, allow_errors: bool = False) -> list[str]:
    return [
        "add",
        "balance",
        "--date",
        date,
        "--account",
        "Expenses:Travel",
        "--amount",
        "25 USD",
        "--pad-from",
        "Equity:Opening-Balances",
        *(["--pad-date", pad_date] if pad_date is not None else []),
        *(["--allow-errors"] if allow_errors else []),
    ]


def _refusal(done: subprocess.CompletedProcess[str], *, as_json: bool, code: int = 1) -> str:
    assert done.returncode == code, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["exit_code"] == code
        assert error["category"] == ("validation" if code == 1 else "usage")
        text = " ".join([error["message"], *error.get("details", [])])
    else:
        text = done.stderr
    return " ".join(text.split())


def _assert_written_pair_and_valid(ledger: Path, done: subprocess.CompletedProcess[str], date: str) -> None:
    assert done.returncode == 0, done.stdout + done.stderr
    text = ledger.read_text()
    assert text.count(" pad Expenses:Travel Equity:Opening-Balances") == 1
    assert "2024-06-01 pad Expenses:Travel Equity:Opening-Balances" in text
    assert re.search(rf"^{date} balance Expenses:Travel\s+25 USD$", text, re.MULTILINE), text
    checked = _bea(ledger, "check", as_json=True)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert json.loads(checked.stdout)["data"]["errors"] == []


@pytest.mark.parametrize("date", ["2024-06-10", "2024-06-02"])
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("allow_errors", [False, True], ids=["strict", "allow-errors"])
def test_an_explicit_pad_date_refusal_names_the_date_that_actually_needs_changing(
    tmp_path: Path, date: str, as_json: bool, allow_errors: bool
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    before = ledger.read_bytes()

    refused = _bea(ledger, *_balance(date, pad_date="2024-05-20", allow_errors=allow_errors), as_json=as_json)
    diagnostic = _refusal(refused, as_json=as_json)

    assert EXPLICIT_HINT.format(pad_date="2024-05-20") in diagnostic
    assert "pads the day before the balance" not in diagnostic
    assert "Date the balance after the open, for example" not in diagnostic
    assert "already holds" not in diagnostic and "need not be added" not in diagnostic
    assert ledger.read_bytes() == before

    # Follow the advertised option, retaining the user's already-valid balance date.
    remedy = re.search(r"pass --pad-date (\d{4}-\d{2}-\d{2}) or later", diagnostic)
    assert remedy is not None
    repaired = _bea(ledger, *_balance(date, pad_date=remedy[1], allow_errors=allow_errors), as_json=as_json)
    _assert_written_pair_and_valid(ledger, repaired, date)


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_an_explicit_date_equal_to_the_default_still_needs_both_flags_when_balance_is_on_open_day(
    tmp_path: Path, as_json: bool
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    before = ledger.read_bytes()

    diagnostic = _refusal(
        _bea(ledger, *_balance("2024-06-01", pad_date="2024-05-31"), as_json=as_json), as_json=as_json
    )

    assert EXPLICIT_HINT.format(pad_date="2024-05-31") in diagnostic
    assert "pads the day before the balance" not in diagnostic
    assert ledger.read_bytes() == before
    # The pad cannot move onto the assertion's own day; the hint also states that constraint.
    still_early = _bea(ledger, *_balance("2024-06-01", pad_date="2024-06-01"), as_json=as_json)
    assert "--pad-date must be earlier than the balance date" in _refusal(still_early, as_json=as_json, code=2)
    assert ledger.read_bytes() == before
    repaired = _bea(ledger, *_balance("2024-06-02", pad_date="2024-06-01"), as_json=as_json)
    _assert_written_pair_and_valid(ledger, repaired, "2024-06-02")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_the_derived_pad_date_keeps_the_balance_date_remedy(tmp_path: Path, as_json: bool) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    before = ledger.read_bytes()

    diagnostic = _refusal(_bea(ledger, *_balance("2024-06-01"), as_json=as_json), as_json=as_json)

    assert "Expenses:Travel opens 2024-06-01, after the pad date 2024-05-31" in diagnostic
    assert "--pad-from pads the day before the balance" in diagnostic
    assert "Date the balance after the open, for example --date 2024-06-02." in diagnostic
    assert "pass --pad-date" not in diagnostic
    assert ledger.read_bytes() == before
    repaired = _bea(ledger, *_balance("2024-06-02"), as_json=as_json)
    _assert_written_pair_and_valid(ledger, repaired, "2024-06-02")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_an_inactive_source_keeps_its_source_account_hint(tmp_path: Path, as_json: bool) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        LEDGER.replace("2024-01-01 open Equity:Opening-Balances", "2024-06-01 open Equity:Opening-Balances").replace(
            "2024-06-01 open Expenses:Travel", "2024-01-01 open Expenses:Travel"
        )
    )
    before = ledger.read_bytes()

    diagnostic = _refusal(
        _bea(ledger, *_balance("2024-06-10", pad_date="2024-05-20", allow_errors=True), as_json=as_json),
        as_json=as_json,
    )

    assert "The --pad-from account must be open on the pad date, 2024-05-20, even with --allow-errors." in diagnostic
    assert "before Expenses:Travel opens" not in diagnostic
    assert "pads the day before the balance" not in diagnostic
    assert ledger.read_bytes() == before
    repaired = _bea(ledger, *_balance("2024-06-10", pad_date="2024-06-01", allow_errors=True), as_json=as_json)
    _assert_written_pair_and_valid(ledger, repaired, "2024-06-10")
