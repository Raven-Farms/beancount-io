"""An importer's unopenable account or malformed commodity is refused as `add` refuses it (w5/637).

Extracted accounts and currencies were only looked up among the ledger's
opens: `Expenses:food stuff` was "not open" with an `add open` remedy, and
`usd` was "open for USD only… or add usd to its open directive", both
remedies `add` itself refuses with exit 2.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
IMPORTER = textwrap.dedent("""
    import datetime
    from decimal import Decimal as D
    from beancount.core import amount, data

    def txn(day, narration, legs):
        postings = [data.Posting(a, amount.Amount(D(n), c), None, None, None, None) for a, n, c in legs]
        meta = data.new_metadata("bank.txt", 1)
        return data.Transaction(meta, day, "*", None, narration, data.EMPTY_SET, data.EMPTY_SET, postings)

    class Base:
        name = "base"

        def identify(self, filepath):
            return True

        def account(self, filepath):
            return "Assets:Checking"

        def extract(self, filepath, existing):
            day = datetime.date(2026, 2, 1)
            return [
                txn(day, "Lunch", [("Expenses:food stuff", "10.00", "USD"), ("Assets:Checking", "-10.00", "USD")]),
                txn(day, "Fee", [("Expenses:Fees", "1.00", "usd"), ("Assets:Checking", "-1.00", "usd")]),
                txn(day, "Dinner", [("Expenses:Dining", "20.00", "USD"), ("Assets:Checking", "-20.00", "USD")]),
                data.Balance(meta=data.new_metadata("bank.txt", 4), date=datetime.date(2026, 2, 3),
                             account="Assets:Checking Account", amount=amount.Amount(D("0"), "USD"),
                             tolerance=None, diff_amount=None),
            ]

    CONFIG = [Base()]
""")


def _rows(tmp_path: Path) -> list[dict[str, Any]]:
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Fees USD\n'
    )
    (tmp_path / "bank.txt").write_text("x\n")
    (tmp_path / "imp.py").write_text(IMPORTER)
    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "bank.txt")]
        + ["--config", str(tmp_path / "imp.py")],
    )
    assert result.exit_code == 0, result.output
    rows: list[dict[str, Any]] = json.loads(result.stdout)["data"]["rows"]
    return rows


def test_each_invalid_name_is_refused_with_adds_words(tmp_path: Path, bea_config_dir: Path) -> None:
    lunch, fee, dinner, balance = _rows(tmp_path)

    assert lunch["status"] == "blocked"
    assert lunch["reason"].startswith("Invalid account 'Expenses:food stuff'.")
    assert "U+0020 (SPACE) is not allowed" in lunch["reason"]
    assert fee["status"] == "blocked"
    assert fee["reason"].startswith("'usd' is not one commodity")
    assert balance["status"] == "blocked"
    assert balance["reason"].startswith("Invalid account 'Assets:Checking Account'.")
    for row in (lunch, fee, balance):
        assert "add open" not in row["reason"] and "to its open directive" not in row["reason"]
        assert row["reason"].endswith("The importer has to return a valid one.")

    # The control: a valid account nothing opens keeps its working remedy.
    assert dinner["status"] == "blocked"
    assert "add open --account Expenses:Dining --date 2026-02-01 -c USD" in dinner["reason"]
