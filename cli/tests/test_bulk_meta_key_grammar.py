"""A bulk row whose metadata key Beancount cannot read rejects its own row (w5/129).

Row validation checked a key's value and the reserved names but not its
spelling, and the printer renders any key. A capitalised `Category` therefore
failed only when the batch was read back: a usage error (exit 2) about
"0 directive(s)" that named neither row nor key and wrote nothing under
`--partial`. A `__` key was dropped silently with exit 0.
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
LEDGER = 'option "operating_currency" "USD"\n2020-01-01 open Assets:Cash USD\n2020-01-01 open Expenses:Food\n'
KEY_RULE = "keys must match [a-z][A-Za-z0-9_-]+"
BAD_KEYS = ["Category", "c", "a b", "a.b", "1a", "_a", "é", "__hidden"]


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


def _row(n: int, meta: dict[str, Any] | None = None, posting_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    food: dict[str, Any] = {"account": "Expenses:Food", "amount": f"1{n - 1} USD"}
    if posting_meta is not None:
        food["meta"] = posting_meta
    row: dict[str, Any] = {
        "date": f"2021-01-0{n + 4}",
        "narration": f"r{n}",
        "postings": [food, {"account": "Assets:Cash"}],
    }
    if meta is not None:
        row["meta"] = meta
    return row


def _run(tmp_path: Path, second: dict[str, Any], *extra: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps([_row(1), second, _row(3)]))
    args = ("--json", "--file", str(ledger), "add", "transactions", "--from", str(rows), *extra)
    return _bea(tmp_path, *args), ledger


@pytest.mark.parametrize("key", BAD_KEYS)
def test_partial_writes_the_other_rows_and_names_the_key(tmp_path: Path, key: str) -> None:
    result, ledger = _run(tmp_path, _row(2, {key: "food"}), "--partial")

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["message"] == "Added 2 of 3 transactions; 1 row was rejected."
    detail = next(d for d in error["details"] if d.startswith(f"Row 2, meta.{key}: "))
    assert repr(key) in detail and KEY_RULE in detail
    assert error["result"] == {"written": 2, "written_rows": [0, 2], "rejected_rows": [1]}
    text = ledger.read_text()
    assert '"r1"' in text and '"r3"' in text and '"r2"' not in text


@pytest.mark.parametrize("key", ["Category", "__hidden"])
def test_without_partial_nothing_is_written(tmp_path: Path, key: str) -> None:
    result, ledger = _run(tmp_path, _row(2, {key: "food"}))

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert any(d.startswith(f"Row 2, meta.{key}: ") and KEY_RULE in d for d in error["details"]), error
    assert error["result"] == {"written": 0, "written_rows": [], "rejected_rows": [1]}
    assert ledger.read_text() == LEDGER


def test_a_posting_key_is_named_by_its_path(tmp_path: Path) -> None:
    result, ledger = _run(tmp_path, _row(2, None, {"Category": "food"}), "--partial")

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert any(d.startswith("Row 2, postings.0.meta.Category: ") and KEY_RULE in d for d in error["details"]), error
    assert error["result"]["written_rows"] == [0, 2]
    assert '"r2"' not in ledger.read_text()


def test_valid_keys_still_write(tmp_path: Path) -> None:
    """Control: every shape the key rule allows is written and reads back."""
    good = _row(2, {"category": "food", "bank_id": "t-1", "aB-9": "x"}, {"ab": "y"})
    result, ledger = _run(tmp_path, good, "--partial")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["written"] == 3
    text = ledger.read_text()
    assert all(line in text for line in ('category: "food"', 'bank_id: "t-1"', 'aB-9: "x"', 'ab: "y"'))
    assert _bea(tmp_path, "--file", str(ledger), "check").returncode == 0
