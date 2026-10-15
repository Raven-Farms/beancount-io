"""A bulk row Beancount cannot read back rejects its own row (w5/184).

The schema takes any string for a posting account and the printer writes it
bare, so `expenses:food` or `Expenses:Food Court` failed only when the batch
was read back: a usage error (exit 2) about "0 directive(s)" that named
neither row nor field and wrote nothing under `--partial`. A keyword for a
currency, a total cost with no currency and a lowercase currency in amount
metadata took the same exit; a non-string one raised a bare AssertionError.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food\n"
BAD_ACCOUNTS = ["expenses:food", "Expenses:Food Court", "Expenses:food", "Expenses", "Expenses:Food:"]
# Schema-valid postings whose rendered text is not one transaction, with a
# fragment of the reason each rejection must carry.
UNREADABLE: dict[str, tuple[dict[str, Any], str, str]] = {
    "keyword currency": ({"amount": "11 TRUE"}, "Row 2: ", "unexpected BOOL"),
    # Refused by the schema now, naming the field rather than the read-back (w5/384).
    "total cost without currency": (
        {"amount": "11 USD", "cost": {"number_total": "5"}},
        "Row 2, postings.0.cost: ",
        'a total cost needs "currency"',
    ),
    "lowercase metadata currency": (
        {"amount": "11 USD", "meta": {"fee": {"kind": "amount", "number": "5", "currency": "usd"}}},
        "Row 2, postings.0.meta.fee: ",
        "currency must be one commodity",
    ),
    "non-string metadata currency": (
        {"amount": "11 USD", "meta": {"fee": {"kind": "amount", "number": "5", "currency": 5}}},
        "Row 2, postings.0.meta.fee: ",
        "currency must be one commodity",
    ),
}


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


def _row(n: int, first: dict[str, Any] | None = None, cash: str = "Assets:Cash") -> dict[str, Any]:
    posting = {"account": "Expenses:Food", "amount": f"1{n - 1} USD"} | (first or {})
    return {"date": f"2026-02-0{n}", "narration": f"r{n}", "postings": [posting, {"account": cash}]}


def _run(
    tmp_path: Path, second: dict[str, Any], *extra: str, ledger_text: str = LEDGER
) -> tuple[subprocess.CompletedProcess[str], Path]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(ledger_text)
    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps([_row(1), second, _row(3)]))
    args = ("--json", "--file", str(ledger), "add", "transactions", "--from", str(rows), *extra)
    return _bea(tmp_path, *args), ledger


@pytest.mark.parametrize("account", BAD_ACCOUNTS)
def test_partial_writes_the_other_rows_and_names_the_account_field(tmp_path: Path, account: str) -> None:
    result, ledger = _run(tmp_path, _row(2, {"account": account}), "--partial")

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["message"] == "Added 2 of 3 transactions; 1 row was rejected."
    detail = next(d for d in error["details"] if d.startswith("Row 2, postings.0.account: "))
    assert f"Invalid account {account!r}" in detail
    assert error["result"] == {"written": 2, "written_rows": [0, 2], "rejected_rows": [1]}
    text = ledger.read_text()
    assert '"r1"' in text and '"r3"' in text and '"r2"' not in text
    assert _bea(tmp_path, "--file", str(ledger), "check").returncode == 0


def test_without_partial_nothing_is_written_and_the_row_is_named(tmp_path: Path) -> None:
    result, ledger = _run(tmp_path, _row(2, {"account": "expenses:food"}))

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert any(
        d.startswith("Row 2, postings.0.account: ") and "Invalid account 'expenses:food'" in d for d in error["details"]
    ), error
    assert error["result"] == {"written": 0, "written_rows": [], "rejected_rows": [1]}
    assert ledger.read_text() == LEDGER


def test_the_balancing_posting_is_named_by_its_own_index(tmp_path: Path) -> None:
    result, ledger = _run(tmp_path, _row(2, cash="assets:cash"), "--partial")

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert any(d.startswith("Row 2, postings.1.account: Invalid account 'assets:cash'") for d in error["details"])
    assert error["result"]["written_rows"] == [0, 2]
    assert '"r2"' not in ledger.read_text()


@pytest.mark.parametrize("case", UNREADABLE)
@pytest.mark.parametrize("partial", [True, False])
def test_a_row_that_does_not_read_back_is_rejected_as_a_row(tmp_path: Path, case: str, partial: bool) -> None:
    posting, prefix, reason = UNREADABLE[case]
    result, ledger = _run(tmp_path, _row(2, posting), *(["--partial"] if partial else []))

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert any(d.startswith(prefix) and reason in d for d in error["details"]), error
    assert error["result"]["rejected_rows"] == [1]
    assert error["result"]["written_rows"] == ([0, 2] if partial else [])
    text = ledger.read_text()
    assert '"r2"' not in text
    assert ('"r1"' in text and '"r3"' in text) if partial else text == LEDGER


def test_an_unknown_account_is_still_the_ledgers_to_reject(tmp_path: Path) -> None:
    """Control: a well-formed name the ledger never opened keeps its suggestion."""
    result, ledger = _run(tmp_path, _row(2, {"account": "Expenses:Foood"}), "--partial")

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert any(d.startswith("Row 2: ") and "unknown account 'Expenses:Foood'" in d for d in error["details"]), error
    assert error["result"] == {"written": 2, "written_rows": [0, 2], "rejected_rows": [1]}
    assert '"r2"' not in ledger.read_text()


def test_well_formed_rows_still_write_on_a_ledger_with_renamed_roots(tmp_path: Path) -> None:
    """Control: the shape check leaves the root to the ledger's own options."""
    renamed = 'option "name_expenses" "Aufwand"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Aufwand:Essen-2\n'
    rows = tmp_path / "rows.json"
    ledger = tmp_path / "main.bean"
    ledger.write_text(renamed)
    rows.write_text(json.dumps([_row(n, {"account": "Aufwand:Essen-2"}) for n in (1, 2, 3)]))

    result = _bea(tmp_path, "--json", "--file", str(ledger), "add", "transactions", "--from", str(rows), "--partial")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["written"] == 3
    assert ledger.read_text().count("Aufwand:Essen-2") == 4
    assert _bea(tmp_path, "--file", str(ledger), "check").returncode == 0
