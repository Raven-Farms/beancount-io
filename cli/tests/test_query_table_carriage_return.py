"""A lone carriage return in ledger text cannot redraw a query table row (w5/108).

Query text tables escaped every control character except CR and LF, kept as
"line breaks". A bare CR is not one: on a terminal it returns the cursor to
column 0, so the rest of a narration was drawn over the row's date and payee
and the row read as a different transaction.

Assertions are on emitted bytes. A terminal turns each `\\n` into `\\r\\n`, so
the PTY check looks for a CR that is not part of a line ending.
"""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_control_character_sanitization import _child_env, _on_a_terminal

FORGED_ROW = "2026-01-06  Landlord  Rent          1.00 USD"
# `\r` and `\n` here are Beancount's own string escapes: the file is printable ASCII.
LEDGER = f"""\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-06 * "Mallory" "x\\r{FORGED_ROW}"
  Expenses:Food  950.00 USD
  Assets:Checking
2026-01-07 * "Bob" "one\\r\\ntwo"
  Expenses:Food  1.00 USD
  Assets:Checking
"""
NARRATIONS = [f"x\r{FORGED_ROW}", "one\r\ntwo"]
QUERY = "SELECT date, payee, narration, position WHERE account ~ 'Food'"
ESCAPED_ROW = f"2026-01-06  Mallory  x\\x0d{FORGED_ROW}".encode()

CR_OUTSIDE_A_LINE_ENDING = re.compile(rb"\r(?!\r*\n)")


def _books(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    return ledger


def _piped(tmp_path: Path, *args: str, stdin: str | None = None) -> bytes:
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        env=_child_env(tmp_path),
        cwd=tmp_path,
        capture_output=True,
        input=None if stdin is None else stdin.encode(),
        stdin=subprocess.DEVNULL if stdin is None else None,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_a_table_on_a_terminal_keeps_the_real_payee(tmp_path: Path) -> None:
    ledger = _books(tmp_path)
    before = ledger.read_bytes()

    emitted = _on_a_terminal(tmp_path, ["--file", str(ledger), "query", QUERY])

    assert ESCAPED_ROW in emitted
    assert CR_OUTSIDE_A_LINE_ENDING.search(emitted) is None, emitted
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("through_the_shell", [False, True], ids=["one-shot", "shell"])
def test_the_text_table_escapes_a_bare_carriage_return(tmp_path: Path, through_the_shell: bool) -> None:
    _books(tmp_path)

    emitted = _piped(tmp_path, "query", stdin=f"{QUERY};\n") if through_the_shell else _piped(tmp_path, "query", QUERY)

    assert ESCAPED_ROW in emitted
    # CRLF is a line break and keeps its shape; it is the only CR left.
    assert b"one\r\ntwo" in emitted
    assert emitted.count(b"\r") == 1


def test_json_and_csv_keep_the_exact_narration(tmp_path: Path) -> None:
    _books(tmp_path)

    as_json = json.loads(_piped(tmp_path, "--json", "query", QUERY))
    as_csv = list(csv.reader(io.StringIO(_piped(tmp_path, "query", "-f", "csv", QUERY).decode(), newline="")))

    assert [row[2] for row in as_json["data"]["rows"]] == NARRATIONS
    assert [row[2] for row in as_csv[1:]] == NARRATIONS
