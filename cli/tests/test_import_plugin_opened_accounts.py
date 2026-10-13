"""Import reads "is this account open" from the ledger as the import would leave it (w5/134).

Blocking was decided on the ledger before the append alone. A ledger that
relies on `auto_accounts` writes no `open` directives, so every row posting to
an account not yet used was refused with an `add open` remedy the ledger's
convention never needs, while `bea add transaction` to that account succeeded.
An importer returning the `open` beside its first transaction was refused the
same way.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

BODY = (
    '2026-01-02 * "Opening balance"\n  Assets:Checking  1000.00 USD\n  Equity:Opening\n\n'
    '2026-08-02 * "Lunch" "elided"\n  Expenses:Food  5.00 USD\n  Assets:Checking\n'
)
AUTO = 'option "operating_currency" "USD"\nplugin "beancount.plugins.auto_accounts"\n\n' + BODY
DECLARED = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking\n"
    "2026-01-01 open Equity:Opening\n"
    "2026-01-01 open Expenses:Food\n\n"
) + BODY
ROWS = ["2026-08-02,Lunch,deli,-5.00", "2026-08-03,Shell,gas,-40.00", "2026-08-04,Other,x,-1.00"]
CSV = "\n".join(["Date,Payee,Narration,Amount", *ROWS]) + "\n"

# Returns the `open` for its category account beside the first transaction.
IMPORTER = """\
import csv, datetime
from decimal import Decimal
from beancount.core.amount import Amount
from beancount.core.data import Open, Posting, Transaction, new_metadata


class Fuel:
    name = "fuel"

    def identify(self, filepath):
        return filepath.endswith(".csv")

    def account(self, filepath):
        return "Assets:Checking"

    def extract(self, filepath, existing):
        out = [Open(new_metadata(filepath, 1), datetime.date(2026, 8, 1), "Expenses:Fuel", OPEN_FOR, None)]
        with open(filepath, newline="") as stream:
            for line, row in enumerate(csv.DictReader(stream), start=2):
                units = Amount(Decimal(row["Amount"]), "USD")
                out.append(
                    Transaction(
                        new_metadata(filepath, line), datetime.date.fromisoformat(row["Date"]),
                        "*", row["Payee"], row["Narration"], frozenset(), frozenset(),
                        [
                            Posting("Assets:Checking", units, None, None, None, None),
                            Posting("Expenses:Fuel", -units, None, None, None, None),
                        ],
                    )
                )
        return out


CONFIG = [Fuel()]
"""


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    (tmp_path / "s.csv").write_text(CSV)
    (tmp_path / "r.toml").write_text('[[rule]]\nmatch = "shell"\naccount = "Expenses:Fuel"\n')
    return tmp_path / "main.bean"


def _import(book: Path, *args: str) -> Any:
    source = str(book.parent / "s.csv")
    return runner.invoke(app, ["--json", "--no-input", "--file", str(book), "import", source, *args])


def _csv(book: Path, *args: str) -> Any:
    return _import(book, "--account", "Assets:Checking", "--rules", str(book.parent / "r.toml"), *args)


def _rows(result: Any) -> list[dict[str, Any]]:
    payload = json.loads(result.stdout or result.stderr)
    rows: list[dict[str, Any]] = (payload["data"] if "data" in payload else payload["error"]["result"])["rows"]
    return rows


def test_auto_accounts_ledger_imports_rows_posting_to_accounts_not_yet_used(book: Path) -> None:
    book.write_text(AUTO)

    preview = _csv(book)

    assert preview.exit_code == 0, preview.output
    assert [row["status"] for row in _rows(preview)] == ["possible_duplicate", "new", "new"]
    assert json.loads(preview.stdout)["data"]["blocked"] == 0
    assert book.read_text() == AUTO

    applied = _csv(book, "--apply", "--duplicates", "skip")

    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.stdout)["data"]["written"] == 2
    written = book.read_text()
    assert written.startswith(AUTO) and "open" not in written.replace("Opening", "")
    assert '2026-08-03 * "Shell" "gas"' in written and "Expenses:Fuel" in written
    assert '2026-08-04 ! "Other" "x"' in written and "Expenses:Uncategorized" in written
    assert '"deli"' not in written
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_without_the_plugin_the_same_rows_stay_blocked(book: Path) -> None:
    book.write_text(DECLARED)

    blocked = _csv(book, "--apply", "--duplicates", "skip")

    assert blocked.exit_code == 4, blocked.output
    rows = _rows(blocked)
    assert [row["status"] for row in rows] == ["possible_duplicate", "blocked", "blocked"]
    assert "Account 'Expenses:Fuel' is not open. Run: bea add open --account Expenses:Fuel" in rows[1]["reason"]
    assert "Account 'Expenses:Uncategorized' is not open." in rows[2]["reason"]
    assert book.read_text() == DECLARED


def test_importer_may_return_the_open_beside_its_first_transaction(book: Path) -> None:
    book.write_text(DECLARED)
    config = book.parent / "imp.py"
    config.write_text(IMPORTER.replace("OPEN_FOR", "None"))

    applied = _import(book, "--config", str(config), "--apply", "--duplicates", "skip")

    assert applied.exit_code == 0, applied.output
    assert [row["status"] for row in _rows(applied)] == ["new", "possible_duplicate", "new", "new"]
    assert json.loads(applied.stdout)["data"]["written"] == 3
    assert "2026-08-01 open Expenses:Fuel" in book.read_text()
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_an_open_in_the_batch_still_restricts_the_currency(book: Path) -> None:
    book.write_text(DECLARED)
    config = book.parent / "imp.py"
    config.write_text(IMPORTER.replace("OPEN_FOR", '["EUR"]'))

    blocked = _import(book, "--config", str(config), "--apply", "--duplicates", "skip")

    assert blocked.exit_code == 4, blocked.output
    reasons = [row["reason"] for row in _rows(blocked) if row["status"] == "blocked"]
    assert len(reasons) == 2 and all(r.startswith("Cannot post USD to 'Expenses:Fuel'") for r in reasons)
    assert book.read_text() == DECLARED
