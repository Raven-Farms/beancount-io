"""A transaction eliding its units beside a zero cost or price is an error at its line (w5/732).

Follow-up to w5/538, which left two booking failures escaping as bare
Python errors: units elided beside a zero cost (`HOOL {0 USD}`) survives
booking with MISSING units and dies in the balance validation on
`abs(MISSING)`, and units elided beside a zero price (`EUR @ 0 USD`)
asserts inside booking. Every read failed naming no file or line, plain
`check` printed upstream's traceback, and the `-p` add failed the same way.
Reads now report `Beancount cannot book this transaction` at the line, and
the single add refuses the posting at input.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from bea_engine import managed_load, protocol
from bea_engine.ledger import adding

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Brokerage
2026-01-01 open Income:Gains USD
2026-01-01 open Equity:Opening
2026-01-02 * "deposit"
  Assets:Checking  10000 USD
  Equity:Opening
2026-02-01 * "missing units with cost"
  Assets:Brokerage  HOOL {0 USD}
  Assets:Checking  -10 USD
2026-02-02 * "missing units with total"
  Assets:Brokerage  HOOL {{0 USD}}
  Assets:Checking  -10 USD
2026-02-03 * "missing units with price"
  Assets:Brokerage  EUR @ 0 USD
  Assets:Checking  -10 EUR
2026-02-04 * "after"
  Assets:Checking  5 USD
  Equity:Opening
"""
COST = (
    "Beancount cannot book this transaction: Assets:Brokerage holds no units beside a zero per-unit cost "
    "({…}), and booking cannot infer units from a zero cost. Give the posting its units, or a nonzero cost."
)
TOTAL = (
    "Beancount cannot book this transaction: Assets:Brokerage holds no units beside a zero total cost "
    "({{…}}), and booking cannot infer units from a zero total. Give the posting its units, or a nonzero total."
)
PRICE = (
    "Beancount cannot book this transaction: Assets:Brokerage holds no units beside a zero price "
    "(@ …), and booking cannot infer units from a zero price. Give the posting its units, or a nonzero price."
)
PYTHON_ERRORS = ("Traceback", "TypeError", "AssertionError", "abs()")


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


@pytest.fixture
def clean(tmp_path: Path) -> Path:
    path = tmp_path / "clean.bean"
    path.write_text(LEDGER.split('2026-02-01 * "missing units with cost"')[0], encoding="utf-8")
    return path


def test_booking_reports_each_transaction_and_resumes_after_it(ledger: Path) -> None:
    entries, errors, _ = managed_load.load_file(ledger)

    unbookable = [
        (error.source["lineno"], error.message)
        for error in errors
        if error.message.startswith(managed_load.CANNOT_BOOK)
    ]
    # Booking-phase failures report before validation-phase ones.
    assert unbookable == [(15, PRICE), (9, COST), (12, TOTAL)]
    for error in errors:
        assert not any(marker in error.message for marker in PYTHON_ERRORS), error.message
    narrations = [getattr(entry, "narration", None) for entry in entries if hasattr(entry, "postings")]
    assert narrations == ["deposit", "after"]


def test_plain_check_names_each_transaction_instead_of_a_traceback(tmp_path: Path, ledger: Path) -> None:
    result = _bea(tmp_path, "check")

    assert result.returncode == 1, result.stderr
    assert not any(marker in result.stderr for marker in PYTHON_ERRORS), result.stderr
    for lineno, message in ((9, COST), (12, TOTAL), (15, PRICE)):
        assert f"{ledger}:{lineno}: {message}" in result.stderr, result.stderr


@pytest.mark.parametrize("command", [["balance"], ["--json", "query", "SELECT account"]])
def test_reads_name_the_file_and_line(tmp_path: Path, ledger: Path, command: list[str]) -> None:
    result = _bea(tmp_path, *command)

    assert result.returncode == 1, result.stdout + result.stderr
    shown = result.stdout + result.stderr
    assert not any(marker in shown for marker in PYTHON_ERRORS), shown
    # ASCII-only prefixes: `--json` escapes the `…` in the tails.
    assert f"{ledger}:9: {COST.split('({…})')[0]}" in shown, shown
    assert f"{ledger}:15: {PRICE.split('(@ …)')[0]}" in shown, shown


@pytest.mark.parametrize(
    ("legs", "tail"),
    [
        (
            ["Assets:Brokerage HOOL {0 USD}", "Assets:Checking -10 USD"],
            "holds no units beside a zero per-unit cost ({…}), and booking cannot infer units from a zero cost. "
            "Give the posting its units, or a nonzero cost.",
        ),
        (
            ["Assets:Brokerage HOOL {{0 USD}}", "Assets:Checking -10 USD"],
            "holds no units beside a zero total cost ({{…}}), and booking cannot infer units from a zero total. "
            "Give the posting its units, or a nonzero total.",
        ),
        (
            ["Assets:Brokerage EUR @ 0 USD", "Assets:Checking -10 EUR"],
            "holds no units beside a zero price (@ …), and booking cannot infer units from a zero price. "
            "Give the posting its units, or a nonzero price.",
        ),
    ],
    ids=["zero-cost", "zero-total", "zero-price"],
)
def test_the_single_add_refuses_elided_units_at_a_zero_rate(clean: Path, legs: list[str], tail: str) -> None:
    request = {"date": "2026-02-01", "narration": "gift", "postings": legs}
    before = clean.read_text(encoding="utf-8")
    with pytest.raises(protocol.UsageError) as raised:
        adding.answer(clean, "transaction", request)

    assert str(raised.value) == f"--posting 1 {tail} Nothing was written."
    assert raised.value.exit_code == 2
    assert clean.read_text(encoding="utf-8") == before


def test_elided_units_at_a_nonzero_cost_still_infer(clean: Path) -> None:
    result = adding.answer(
        clean,
        "transaction",
        {
            "date": "2026-02-01",
            "narration": "gift",
            "postings": ["Assets:Brokerage HOOL {5 USD}", "Assets:Checking -10 USD"],
        },
    )

    assert result["written"] == 1
    assert "HOOL {5 USD}" in clean.read_text(encoding="utf-8")
