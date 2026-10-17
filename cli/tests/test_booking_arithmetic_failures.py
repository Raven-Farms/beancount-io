"""A transaction booking cannot do the arithmetic for is an error at its line (w5/538).

Beancount's booking raises instead of reporting when a zero-unit posting
divides a total cost by nothing (`0 HOOL {{310 USD}}`) or an amount it infers
does not fit its 28-digit context. Every read failed with a bare
`DivisionByZero` or `InvalidOperation` naming no file or line, plain `check`
printed upstream's traceback, and one such bulk row aborted a whole
`--partial` batch. Booking now reports the transaction, drops it and resumes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from bea_engine import managed_load, protocol
from bea_engine.ledger import adding

ROOT = Path(__file__).resolve().parents[1]

WIDE = "12345678901.123456789012345678"  # 29 significant digits
LEDGER = f"""\
option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Assets:Broker
2026-01-01 open Equity:Opening
2026-02-01 * "buy"
  Assets:Broker  10 HOOL {{10 USD}}
  Assets:Cash  -100 USD
2026-02-02 * "zero units"
  Assets:Broker  0 HOOL {{{{10 USD}}}}
  Assets:Cash  -10 USD
2026-02-03 * "too wide to infer"
  Assets:Broker  {WIDE} SHIB
  Equity:Opening
2026-02-04 * "sell from the lot bought before both"
  Assets:Broker  -4 HOOL {{}}
  Assets:Cash  40 USD
"""
ZERO = (
    "Beancount cannot book this transaction: Assets:Broker holds zero units at a total cost ({{…}}), and booking "
    "divides the total by the units. Give the posting its units, or write its cost per unit in single braces."
)
TOO_WIDE = (
    "Beancount cannot book this transaction: it has to calculate an amount wider than the 28 significant digits "
    "its arithmetic keeps, which happens when a posting's amount is left for it to infer beside a number that "
    "wide. Give every posting an explicit amount, or use a number of at most 28 significant digits."
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        timeout=120,
    )


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def test_booking_reports_each_transaction_and_resumes_after_it(ledger: Path) -> None:
    entries, errors, _ = managed_load.load_file(ledger)

    assert [(error.source["lineno"], error.message) for error in errors] == [(8, ZERO), (11, TOO_WIDE)]
    narrations = [getattr(entry, "narration", None) for entry in entries if hasattr(entry, "postings")]
    assert narrations == ["buy", "sell from the lot bought before both"]
    # The sale booked against the lot the purchase left, so the balances
    # booking resumed from were the ones it had reached.
    sale = entries[-1].postings[0]
    assert sale.units.number == Decimal(-4) and sale.cost.number == Decimal(10)


def test_plain_check_names_each_transaction_instead_of_a_traceback(tmp_path: Path, ledger: Path) -> None:
    result = _bea(tmp_path, "check")

    assert result.returncode == 1, result.stderr
    assert result.stderr.splitlines() == [
        f"Error: {ledger}: 2 error(s).",
        f"  {ledger}:8: {ZERO}",
        f"  {ledger}:11: {TOO_WIDE}",
    ]


def test_check_with_bean_check_options_does_not_reach_its_traceback(tmp_path: Path, ledger: Path) -> None:
    result = _bea(tmp_path, "check", "-v")

    assert result.returncode == 1, result.stderr
    assert "Traceback" not in result.stderr
    assert f"{ledger}:8: {ZERO}" in result.stderr and f"{ledger}:11: {TOO_WIDE}" in result.stderr


@pytest.mark.parametrize("command", [["--json", "check"], ["balance"], ["--json", "query", "SELECT account"]])
def test_reads_name_the_file_and_line(tmp_path: Path, ledger: Path, command: list[str]) -> None:
    result = _bea(tmp_path, *command)

    assert result.returncode == 1, result.stdout + result.stderr
    out = result.stdout + result.stderr
    assert "DivisionByZero" not in out and "InvalidOperation" not in out
    assert "main.bean:8: Beancount cannot book this transaction: Assets:Broker holds zero units" in out
    assert "main.bean:11: Beancount cannot book this transaction: it has to calculate" in out


def _row(narration: str, *postings: dict[str, Any]) -> dict[str, Any]:
    return {"date": "2026-03-01", "narration": narration, "postings": list(postings)}


OK = _row("ok", {"account": "Assets:Cash", "amount": "-5 USD"}, {"account": "Equity:Opening"})
ZERO_ROW = _row(
    "zero units",
    {
        "account": "Assets:Broker",
        "units": {"number": "0", "currency": "HOOL"},
        "cost": {"number_total": "310", "currency": "USD"},
    },
    {"account": "Assets:Cash", "amount": "-310 USD"},
)
WIDE_ROW = _row("too wide", {"account": "Assets:Broker", "amount": f"{WIDE} SHIB"}, {"account": "Equity:Opening"})


@pytest.fixture
def clean(tmp_path: Path) -> Path:
    path = tmp_path / "clean.bean"
    path.write_text(LEDGER.split('2026-02-01 * "buy"')[0], encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("bad", "detail"),
    [
        (
            ZERO_ROW,
            "Row 2, postings.0: Value error, the posting holds zero units at a total cost ({{…}}), and booking "
            "divides the total by the units. Give the posting its units, or write its cost per unit in single braces.",
        ),
        (WIDE_ROW, f"Row 2: Proposed append (not written): {TOO_WIDE}"),
    ],
    ids=["zero-units", "too-wide"],
)
def test_partial_rejects_only_the_row_and_writes_the_rest(clean: Path, bad: dict[str, Any], detail: str) -> None:
    with pytest.raises(protocol.LedgerError) as raised:
        adding.answer(clean, "transactions", {"rows": [OK, bad, OK], "partial": True})

    assert str(raised.value) == "Added 2 of 3 transactions; 1 row was rejected."
    assert raised.value.details[0] == detail
    assert raised.value.result is not None and raised.value.result["rejected_rows"] == [1]
    assert clean.read_text().count('"ok"') == 2


def test_the_atomic_refusal_names_the_row(clean: Path) -> None:
    before = clean.read_text()
    with pytest.raises(protocol.LedgerError) as raised:
        adding.answer(clean, "transactions", {"rows": [OK, WIDE_ROW, OK]})

    assert str(raised.value).endswith("Pass --partial to append the 2 valid rows."), raised.value
    assert raised.value.details == [f"Row 2: Proposed append (not written): {TOO_WIDE}"]
    assert clean.read_text() == before


@pytest.mark.parametrize("cost", ["{{310 USD}}", "{10 # 310 USD}"])
def test_the_single_add_refuses_zero_units_at_a_total_cost(clean: Path, cost: str) -> None:
    request = {
        "date": "2026-03-01",
        "narration": "zero",
        "postings": [f"Assets:Broker 0 HOOL {cost}", "Assets:Cash -310 USD"],
    }
    before = clean.read_text()
    with pytest.raises(protocol.UsageError) as raised:
        adding.answer(clean, "transaction", request)

    assert str(raised.value) == (
        "--posting 1 holds zero units at a total cost ({{…}}), and booking divides the total by the units. "
        "Give the posting its units, or write its cost per unit in single braces. Nothing was written."
    )
    assert raised.value.exit_code == 2
    assert clean.read_text() == before
