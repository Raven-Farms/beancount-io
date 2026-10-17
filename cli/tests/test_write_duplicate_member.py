"""A write into a file the ledger also reaches under a second name validates against one copy (w5/574).

Reads load such a file once and report `Duplicate include` (w5/433). A write
staged only the target's own path; the second name (a link the include glob
matches) still reached the original, and the candidate's new inode hid it from
the duplicate check. The original's entries were loaded beside the
candidate's: a wrong assertion was written, a right one refused, and the
existing-error gate was skipped.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = (
    'option "operating_currency" "USD"\n2020-01-01 open Assets:Bank USD\n2020-01-01 open Expenses:Food USD\n'
    'include "txns/*.bean"\n'
)
TXNS = '2020-01-03 * "Shop" "food"\n  Expenses:Food  10.00 USD\n  Assets:Bank\n'


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    (tmp_path / "txns").mkdir()
    (tmp_path / "txns" / "2020.bean").write_text(TXNS)
    (tmp_path / "txns" / "current.bean").symlink_to("2020.bean")
    main = tmp_path / "main.bean"
    main.write_text(MAIN)
    return main


def _bea(ledger: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(ledger.parent / ".config"),
        XDG_CACHE_HOME=str(ledger.parent / ".cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(ledger), *args],
        env=env,
        cwd=ledger.parent,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _balance(amount: str) -> list[str]:
    return ["add", "balance", "--date", "2020-03-01", "--account", "Assets:Bank", "--amount", amount]


def test_an_assertion_is_judged_against_the_file_counted_once(ledger: Path) -> None:
    target = ledger.parent / "txns" / "2020.bean"

    wrong = _bea(ledger, *_balance("-20.00 USD"), "--into", "txns/2020.bean", "--allow-errors")
    assert wrong.returncode == 1, wrong.stdout + wrong.stderr
    assert "expected -20.00 USD != accumulated -10.00 USD" in wrong.stderr
    assert target.read_text() == TXNS

    right = _bea(ledger, *_balance("-10.00 USD"), "--into", "txns/2020.bean", "--allow-errors")
    assert right.returncode == 0, right.stdout + right.stderr
    assert "balance Assets:Bank" in target.read_text()
    check = _bea(ledger, "check")
    assert "Balance failed" not in check.stdout + check.stderr
    assert "Duplicate include" in check.stdout + check.stderr


def test_the_existing_duplicate_include_still_gates_a_write(ledger: Path) -> None:
    result = _bea(
        ledger,
        "add",
        "transaction",
        "X",
        "--date",
        "2020-02-02",
        "-p",
        "Expenses:Food 1.00 USD",
        "-p",
        "Assets:Bank",
        "--into",
        "txns/2020.bean",
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "The ledger already has 1 error(s)" in result.stderr
    assert f"{ledger}:4: Duplicate include:" in result.stderr
    assert (ledger.parent / "txns" / "2020.bean").read_text() == TXNS


def test_a_root_write_names_the_include_line_not_a_staging_file(ledger: Path) -> None:
    result = _bea(
        ledger,
        "add",
        "transaction",
        "X",
        "--date",
        "2020-02-02",
        "-p",
        "Expenses:Food 1.00 USD",
        "-p",
        "Assets:Bank",
        "--allow-errors",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{ledger}:4: Duplicate include:" in result.stdout + result.stderr
    assert ".bea-" not in result.stdout + result.stderr
