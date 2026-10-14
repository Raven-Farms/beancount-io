"""The import preview's diff shows existing ledger lines with controls escaped (w5/244).

The unified diff under the preview table carries the last lines of the
existing ledger as context, and it was echoed byte for byte. A hand-edited or
third-party ledger whose tail held cursor-movement sequences could therefore
repaint the summary table above it, on the one screen `--apply` is gated on.
Text mode now shows those bytes as `\\x1b…`; `--json` keeps the exact value.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

ESC = "\x1b"
HEAD = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Uncategorized USD
"""
FAKE_ROW = "1    new     2026-02-01  Coffee shop        -12.34 USD     hash  unmatched"
HOSTILE = f"; statement marker{ESC}[7A{ESC}[2K{ESC}[G{FAKE_ROW}{ESC}[7B{ESC}[2K{ESC}[G ; statement marker\n"
SHOWN = f" ; statement marker\\x1b[7A\\x1b[2K\\x1b[G{FAKE_ROW}\\x1b[7B\\x1b[2K\\x1b[G ; statement marker\n"
CSV = "Date,Amount,Description\n2026-02-01,-9912.34,Wire to M. Allory\n2026-02-02,-5.00,Lunch\n"


def _import(tmp_path: Path, tail: str, *extra: str, json_mode: bool = False) -> str:
    ledger = tmp_path / "main.bean"
    ledger.write_text(HEAD + tail)
    source = tmp_path / "bank.csv"
    source.write_text(CSV)
    argv = [*(["--json"] if json_mode else []), "--no-input", "--file", str(ledger)]
    argv += ["import", str(source), "--csv", "auto", "--account", "Assets:Cash", *extra]
    # `color=True` stands in for a terminal: without it Click strips escape
    # sequences from a captured stream, which is not what a PTY receives.
    result = CliRunner().invoke(app, argv, color=True)
    assert result.exit_code == 0, result.output
    return result.stdout


@pytest.mark.parametrize("extra", [(), ("--apply",)], ids=["preview", "apply"])
def test_escape_sequences_in_the_ledger_tail_are_shown_not_sent(tmp_path: Path, extra: tuple[str, ...]) -> None:
    out = _import(tmp_path, HOSTILE, *extra)

    assert ESC not in out
    assert SHOWN in out
    # The proposed entry still shows the true amount.
    assert "+  Assets:Cash             -9912.34 USD\n" in out


def test_json_keeps_the_exact_diff(tmp_path: Path) -> None:
    diff = json.loads(_import(tmp_path, HOSTILE, json_mode=True))["data"]["diff"]

    assert f" {HOSTILE}" in diff


def test_a_plain_ledger_diff_is_unchanged(tmp_path: Path) -> None:
    text = _import(tmp_path, "; statement marker\n")
    diff = json.loads(_import(tmp_path, "; statement marker\n", json_mode=True))["data"]["diff"]

    assert " ; statement marker\n+\n" in diff
    assert diff in text
