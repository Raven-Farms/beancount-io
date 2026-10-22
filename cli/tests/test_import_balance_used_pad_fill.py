"""An imported statement balance is never silently padded by a used pad (w5/871).

The follow-up to w5/796: `add balance` refuses a gap a pad consumed by an
earlier assertion would fill in a currency it has not padded yet, but an
importer's `Balance` went through the batch validation, which the pad passes,
and `--apply` wrote it with a backdated 50.00 EUR adjustment, exit 0.
"""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from cli.main import app
from tests.test_add_balance_used_pad_fill import LEDGER

runner = CliRunner()
IMPORTER = textwrap.dedent("""
    import datetime
    from decimal import Decimal as D
    from beancount.core import amount, data

    class Statement:
        name = "statement"

        def identify(self, filepath):
            return True

        def account(self, filepath):
            return "Assets:Checking"

        def extract(self, filepath, existing):
            meta = data.new_metadata(filepath, 1)
            return [data.Balance(meta, datetime.date(2026, 3, 15), "Assets:Checking",
                                 amount.Amount(D("{number}"), "EUR"), None, None)]

    CONFIG = [Statement()]
""")


def _import(tmp_path: Path, number: str, *flags: str) -> Any:
    ledger = tmp_path / "mc.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "statement.txt").write_text("x\n")
    (tmp_path / "imp.py").write_text(IMPORTER.replace("{number}", number))
    return runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(tmp_path / "statement.txt")]
        + ["--config", str(tmp_path / "imp.py"), *flags],
    )


def test_the_preview_blocks_the_padded_balance_naming_the_pad(tmp_path: Path, bea_config_dir: Path) -> None:
    result = _import(tmp_path, "250.00")

    assert result.exit_code == 0, result.output
    (row,) = json.loads(result.stdout)["data"]["rows"]
    assert row["status"] == "blocked"
    assert row["reason"].startswith("Assets:Checking holds 200.00 EUR on 2026-03-15 but this row asserts 250.00")
    assert f"the pad at {tmp_path / 'mc.bean'}:10 (2026-01-09 from Equity:OpeningBalances)" in row["reason"]
    assert "would silently insert the 50.00 EUR difference" in row["reason"]


def test_apply_writes_nothing(tmp_path: Path, bea_config_dir: Path) -> None:
    result = _import(tmp_path, "250.00", "--apply")

    assert result.exit_code == 4, result.output
    error = json.loads(result.stderr)["error"]
    assert "1 row is blocked by a pad that would silently fill the gap; resolve it first." in error["message"]
    assert "unopened account" not in error["message"]
    assert any("would silently insert the 50.00 EUR difference" in line for line in error["details"])
    assert (tmp_path / "mc.bean").read_text() == LEDGER


def test_a_balance_that_agrees_is_still_written(tmp_path: Path, bea_config_dir: Path) -> None:
    result = _import(tmp_path, "200.00", "--apply")

    assert result.exit_code == 0, result.output
    assert re.search(r"2026-03-15 balance Assets:Checking +200\.00 EUR", (tmp_path / "mc.bean").read_text())


def test_the_printed_pad_command_is_complete_and_runs(tmp_path: Path, bea_config_dir: Path) -> None:
    """The remedy names the account, date and amount of the row (w5/873)."""
    import shlex

    result = _import(tmp_path, "250.00", "--apply")
    (reason,) = [line for line in json.loads(result.stderr)["error"]["details"] if "pads it explicitly" in line]
    command = re.search(r"(bea .*?) pads it explicitly", reason)
    assert command is not None
    argv = shlex.split(command.group(1))
    assert argv[argv.index("add") :] == [
        "add",
        "balance",
        "--account",
        "Assets:Checking",
        "--date",
        "2026-03-15",
        "--amount",
        "250.00 EUR",
        "--pad-from",
        "Equity:OpeningBalances",
    ]
    ran = runner.invoke(app, ["--file", str(tmp_path / "mc.bean"), *argv[1:]])
    assert ran.exit_code == 0, ran.output


def test_the_blocked_summary_names_every_cause() -> None:
    from bea_engine.importing import _blocked_summary

    assert _blocked_summary(0, 0) == ""
    assert _blocked_summary(1, 0).startswith(" 1 row is blocked by an unopened account or a currency mismatch;")
    assert _blocked_summary(2, 2) == " 2 rows are blocked by pads that would silently fill the gap; resolve them first."
    assert _blocked_summary(3, 1) == (
        " 3 rows are blocked by unopened accounts or currency mismatches and a pad that would silently fill the gap;"
        " resolve them first."
    )
