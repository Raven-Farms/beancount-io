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
    assert "1 row is blocked" in error["message"]
    assert any("would silently insert the 50.00 EUR difference" in line for line in error["details"])
    assert (tmp_path / "mc.bean").read_text() == LEDGER


def test_a_balance_that_agrees_is_still_written(tmp_path: Path, bea_config_dir: Path) -> None:
    result = _import(tmp_path, "200.00", "--apply")

    assert result.exit_code == 0, result.output
    assert re.search(r"2026-03-15 balance Assets:Checking +200\.00 EUR", (tmp_path / "mc.bean").read_text())
