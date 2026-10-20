"""Rows that are not posted are left out, named, and never stop the import (w5/831).

After w5/614: a pending row with a blank posted date refused the whole import
with no `status=` hint; with `status=` mapped, a `Pending` date cell still
refused it, because date inference read the left-out row; and `Temporary
Hold`, `Pre-authorized`, `Declined` or `Reverted` rows were imported as posted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from bea_engine import csv_mapper as engine
from cli import csv_mapper as frontend
from cli.main import app

runner = CliRunner()
LEDGER = (
    'option "operating_currency" "USD"\n2026-01-01 open Liabilities:CreditCard USD\n'
    "2026-01-01 open Expenses:Dining USD\n2026-01-01 open Expenses:Uncategorized USD\n"
)


def _import(tmp_path: Path, body: str, mapping: str, *flags: str) -> Any:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "card.csv").write_text(body)
    return runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "card.csv")]
        + ["--csv", mapping, "--account", "Liabilities:CreditCard", *flags],
    )


def test_a_blank_pending_date_points_at_status(tmp_path: Path, bea_config_dir: Path) -> None:
    body = "Posted Date,Description,Amount,Status\n09/28/2026,BLUE BOTTLE,-4.50,Posted\n,BISTRO 9,-50.00,Pending\n"

    result = _import(tmp_path, body, "date=Posted Date,narration=Description,amount=Amount", "--apply")

    assert result.exit_code == 2, result.output
    message = json.loads(result.stderr)["error"]["message"]
    assert "Column 'Status' marks this row 'Pending': add status=Status to the --csv mapping" in message
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_a_pending_date_cell_is_not_read_for_the_format(tmp_path: Path, bea_config_dir: Path) -> None:
    body = (
        "Posted Date,Description,Amount,Status\n09/28/2026,BLUE BOTTLE,-4.50,Posted\nPending,BISTRO 9,-50.00,Pending\n"
    )

    result = _import(tmp_path, body, "date=Posted Date,narration=Description,amount=Amount,status=Status")

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    assert [row["row"] for row in data["rows"]] == [1]
    assert data["skipped_pending"] == 1


def test_holds_authorizations_and_declines_are_left_out(tmp_path: Path, bea_config_dir: Path) -> None:
    statuses = ["Posted", "Temporary Hold", "On-Hold", "Pre-authorized", "Declined", "Reverted", "Pending"]
    body = "Date,Description,Amount,Status\n" + "".join(
        f"2026-09-28,R{index},-{index + 1}.00,{status}\n" for index, status in enumerate(statuses)
    )

    result = _import(tmp_path, body, "date=Date,narration=Description,amount=Amount,status=Status")

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    assert [row["narration"] for row in data["rows"]] == ["R0"]
    assert data["skipped_pending"] == 6
    notes = " ".join(data["notes"])
    assert "Left out 4 pending row(s)" in notes
    assert "Left out 2 row(s) whose status says they never posted" in notes


def test_the_frontend_and_engine_read_the_same_statuses() -> None:
    assert engine.PENDING_STATUSES | engine.NEVER_POSTED_STATUSES == frontend.UNPOSTED_STATUSES
    for word in [*frontend.UNPOSTED_STATUSES, "Pending", "pending review", "Posted", "Completed", ""]:
        assert engine.is_pending(word) is frontend.is_unposted(word), word
