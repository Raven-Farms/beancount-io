"""A blocked row's `add open` remedy fixes the whole import, not only its own row (w5/076).

Each row suggested opening the missing account on that row's date. Exports
usually list the newest row first, so the first suggestion opened the account
after the older rows and the retry failed on an inactive account.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking\n"
    "2026-01-01 open Expenses:Uncategorized\n"
    "2026-01-01 open Equity:Opening\n\n"
    '2026-01-02 * "Opening balance"\n  Assets:Checking  1000.00 USD\n  Equity:Opening\n'
)
NEWEST_FIRST = ["2026-03-20,Shell gas,-40.00", "2026-02-10,Shell gas,-35.00", "2026-01-15,Shell gas,-30.00"]
REMEDY = "add open --account Expenses:Fuel --date 2026-01-15 -c USD"

IMPORTER = """\
import csv, datetime
from decimal import Decimal
from beancount.core.amount import Amount
from beancount.core.data import Posting, Transaction, new_metadata


class Fuel:
    name = "fuel"

    def identify(self, filepath):
        return filepath.endswith(".csv")

    def account(self, filepath):
        return "Assets:Checking"

    def extract(self, filepath, existing):
        out = []
        with open(filepath, newline="") as stream:
            for line, row in enumerate(csv.DictReader(stream), start=2):
                units = Amount(Decimal(row["Amount"]), row.get("Currency") or "USD")
                out.append(
                    Transaction(
                        new_metadata(filepath, line), datetime.date.fromisoformat(row["Date"]),
                        "*", None, row["Description"], frozenset(), frozenset(),
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
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "rules.toml").write_text('[[rule]]\nmatch = "shell"\naccount = "Expenses:Fuel"\n')
    (tmp_path / "imp.py").write_text(IMPORTER)
    return ledger


def _import(book: Path, rows: list[str], mode: str, *args: str, header: str = "Date,Description,Amount") -> Any:
    source = book.parent / "a.csv"
    source.write_text("\n".join([header, *rows]) + "\n")
    how = (
        ["--account", "Assets:Checking", "--rules", str(book.parent / "rules.toml")]
        if mode == "csv"
        else ["--config", str(book.parent / "imp.py")]
    )
    return runner.invoke(app, ["--json", "--no-input", "--file", str(book), "import", str(source), *how, *args])


def _reasons(result: Any) -> list[str]:
    payload = json.loads(result.stdout or result.stderr)
    rows = payload["data"]["rows"] if "data" in payload else payload["error"]["result"]["rows"]
    return [row["reason"] for row in rows]


@pytest.mark.parametrize("mode", ["csv", "importer"])
@pytest.mark.parametrize("order", ["newest-first", "oldest-first"])
def test_every_blocked_row_gives_the_one_command_that_unblocks_the_import(book: Path, mode: str, order: str) -> None:
    rows = NEWEST_FIRST if order == "newest-first" else NEWEST_FIRST[::-1]

    blocked = _import(book, rows, mode, "--apply")

    assert blocked.exit_code == 4, blocked.output
    reasons = _reasons(blocked)
    assert len(reasons) == 3 and all(reason.endswith(f" {REMEDY}.") for reason in reasons)
    assert book.read_text() == LEDGER
    opened = runner.invoke(app, ["--file", str(book), *shlex.split(REMEDY)])
    assert opened.exit_code == 0, opened.output
    applied = _import(book, rows, mode, "--apply")
    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.stdout)["data"]["written"] == 3
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_the_human_review_lines_carry_the_same_command(book: Path) -> None:
    source = book.parent / "a.csv"
    source.write_text("\n".join(["Date,Description,Amount", *NEWEST_FIRST]) + "\n")

    result = runner.invoke(
        app,
        ["--no-input", "--file", str(book), "import", str(source), "--account", "Assets:Checking"]
        + ["--rules", str(book.parent / "rules.toml"), "--apply"],
    )

    assert result.exit_code == 4, result.output
    flat = " ".join(result.output.split())
    assert flat.count(REMEDY) == 3
    assert "--date 2026-03-20" not in flat and "--date 2026-02-10" not in flat


def test_the_command_allows_every_currency_the_import_posts_to_the_account(book: Path) -> None:
    rows = ["2026-03-20,Shell gas,-40.00,EUR", "2026-01-15,Shell gas,-30.00,USD"]
    remedy = "add open --account Expenses:Fuel --date 2026-01-15 -c EUR -c USD"

    blocked = _import(book, rows, "importer", "--apply", header="Date,Description,Amount,Currency")

    assert all(reason.endswith(f" {remedy}.") for reason in _reasons(blocked))
    assert runner.invoke(app, ["--file", str(book), *shlex.split(remedy)]).exit_code == 0
    applied = _import(book, rows, "importer", "--apply", header="Date,Description,Amount,Currency")
    assert applied.exit_code == 0, applied.output
