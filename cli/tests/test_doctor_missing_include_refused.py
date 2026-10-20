"""`doctor missing-open`, `linked` and `region` refuse a ledger whose include is missing (w5/819).

w5/596 refused a load a syntax error left partial; a missing include hides
its directives just as surely. `missing-open main.bean` listed the opens the
absent `accounts.bean` held, exit 0, ready for the documented `>> main.bean`
to append them twice, and `linked` showed half a link group.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
include "accounts.bean"
include "trips.bean"
2026-01-10 * "Rent" ^trip
  Expenses:Rent 9.00 USD
  Assets:Bank
"""
TRIPS = '2026-01-12 * "Taxi" ^trip\n  Expenses:Taxi 3.00 USD\n  Assets:Bank\n'
ACCOUNTS = "2026-01-01 open Assets:Bank USD\n2026-01-01 open Expenses:Rent USD\n2026-01-01 open Expenses:Taxi USD\n"


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "trips.bean").write_text(TRIPS)
    return tmp_path


def _doctor(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "doctor", *args],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


OPERATIONS = {
    "missing-open": lambda books: ["missing-open", str(books / "main.bean")],
    "linked": lambda books: ["linked", str(books / "main.bean"), f"{books / 'main.bean'}:4"],
    "region": lambda books: ["region", str(books / "main.bean"), f"{books / 'main.bean'}:4:6"],
}


@pytest.mark.parametrize("op", sorted(OPERATIONS))
def test_a_missing_include_is_named_before_any_output(books: Path, op: str) -> None:
    result = _doctor(books, *OPERATIONS[op](books))

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout == ""
    message = " ".join(result.stderr.split())
    assert (
        f'doctor {op} cannot load {books / "main.bean"}: missing include "accounts.bean" '
        f"(included by {books / 'main.bean'})"
    ) in message


def test_with_the_include_present_missing_open_answers(books: Path) -> None:
    (books / "accounts.bean").write_text(ACCOUNTS)

    result = _doctor(books, "missing-open", str(books / "main.bean"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "open" not in result.stdout
