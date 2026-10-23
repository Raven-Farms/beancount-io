"""A possible duplicate's reason names only the bank IDs that exist (w5/615).

Two identical same-day charges in one export were flagged, correctly, with
"different bank IDs do not rule out a duplicate", about IDs neither row
had, which misled an agent deciding whether to skip.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Liabilities:CreditCard USD\n"
    "2026-01-01 open Expenses:Uncategorized USD\n"
)


def _rows(tmp_path: Path, csv: str, mapping: str, ledger: str = LEDGER) -> list[dict[str, Any]]:
    (tmp_path / "main.bean").write_text(ledger)
    (tmp_path / "n.csv").write_text(csv)
    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "n.csv")]
        + ["--csv", mapping, "--account", "Liabilities:CreditCard"],
    )
    assert result.exit_code == 0, result.output
    rows: list[dict[str, Any]] = json.loads(result.stdout)["data"]["rows"]
    return rows


def test_a_repeat_in_one_export_names_the_row_and_no_ids(tmp_path: Path, bea_config_dir: Path) -> None:
    rows = _rows(
        tmp_path,
        "Date,Description,Amount\n10/04/2026,NETFLIX.COM,-15.49\n10/04/2026,NETFLIX.COM,-15.49\n",
        "date=Date,narration=Description,amount=Amount",
    )

    assert rows[1]["status"] == "possible_duplicate"
    assert (
        rows[1]["reason"] == "Date, narration and source amount match row 1 of this import; neither row has a bank ID."
    )


def test_a_ledger_twin_without_ids_says_so(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = LEDGER + '2026-10-04 * "NETFLIX.COM"\n  Liabilities:CreditCard  -15.49 USD\n  Expenses:Uncategorized\n'

    (row,) = _rows(
        tmp_path,
        "Date,Description,Amount\n10/04/2026,NETFLIX.COM,-15.49\n",
        "date=Date,narration=Description,amount=Amount",
        ledger,
    )

    assert row["reason"] == "Date, narration and source amount match; neither has a bank ID."


def test_different_ids_on_both_sides_are_named(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = (
        LEDGER
        + '2026-10-04 * "NETFLIX.COM"\n  import-id: "bank:A1"\n  bank_id: "A1"\n'
        + "  Liabilities:CreditCard  -15.49 USD\n  Expenses:Uncategorized\n"
    )

    (row,) = _rows(
        tmp_path,
        "Date,Description,Amount,ID\n10/04/2026,NETFLIX.COM,-15.49,B2\n",
        "date=Date,narration=Description,amount=Amount,id=ID",
        ledger,
    )

    assert (
        row["reason"]
        == "Date, narration and source amount match; their bank IDs differ, which does not rule out a duplicate."
    )


IMPORTER = """
import datetime, hashlib
from decimal import Decimal as D
from beancount.core import amount, data

def _id(row, n):
    base = f"2026-10-04|-15.49|NETFLIX.COM|Liabilities:CreditCard" + (f"|{n}" if n else "")
    return "csv:sha256:" + hashlib.sha256(base.encode()).hexdigest()[:16]

class Card:
    name = "card"
    def identify(self, filepath):
        return True
    def account(self, filepath):
        return "Liabilities:CreditCard"
    def extract(self, filepath, existing):
        rows = []
        for n in range(2):
            meta = data.new_metadata(filepath, n + 1)
            meta["import-id"] = _id(None, n)
            legs = [data.Posting(a, amount.Amount(D(v), "USD"), None, None, None, None)
                    for a, v in (("Liabilities:CreditCard", "-15.49"), ("Expenses:Uncategorized", "15.49"))]
            rows.append(data.Transaction(meta, datetime.date(2026, 10, 4), "*", None, "NETFLIX.COM",
                                         data.EMPTY_SET, data.EMPTY_SET, legs))
        return rows

CONFIG = [Card()]
"""


def test_an_importers_generated_ids_are_no_bank_ids(tmp_path: Path, bea_config_dir: Path) -> None:
    """Rows with importer-generated `csv:sha256:` ids were told "only one of them carries a bank ID" (w5/832)."""
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "n.csv").write_text("x\n")
    (tmp_path / "imp.py").write_text(IMPORTER)

    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "n.csv")]
        + ["--config", str(tmp_path / "imp.py")],
    )

    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout)["data"]["rows"]
    assert rows[1]["status"] == "possible_duplicate"
    assert rows[1]["reason"].endswith("neither row has a bank ID.")
