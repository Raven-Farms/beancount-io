"""Importer rows that cannot be written are named by their row (w5/638).

An unbalanced row previewed as `new`, counted ready under "repeat with
--apply", and `--apply` refused naming no row. An uppercase metadata key
stopped even the preview with a usage error numbering only the ready rows
("Directive 2 of 3"). A string or datetime date, and a source posting with no
amount, failed as bare Python errors or without the row.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n'
BASE = textwrap.dedent("""
    import datetime
    from decimal import Decimal as D
    from beancount.core import amount, data
    from beancount.core.inventory import Inventory

    def txn(day, narration, a="-3.00", b="3.00", meta=None, account="Expenses:Food", units=True, pmeta=None):
        m = data.new_metadata("bank.txt", 1)
        m.update(meta or {})
        src = data.Posting("Assets:Checking", amount.Amount(D(a), "USD") if units else None, None, None, None, None)
        dst = data.Posting(account, amount.Amount(D(b), "USD"), None, None, None, pmeta)
        return data.Transaction(m, day, "*", None, narration, data.EMPTY_SET, data.EMPTY_SET, [src, dst])

    def day(n):
        return datetime.date(2026, 2, n)

    class Base:
        name = "base"

        def __init__(self, rows):
            self.rows = rows

        def identify(self, filepath):
            return True

        def account(self, filepath):
            return "Assets:Checking"

        def extract(self, filepath, existing):
            return self.rows
""")


def _import(tmp_path: Path, rows: str, *args: str) -> Any:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.txt").write_text("x\n")
    (tmp_path / "base.py").write_text(BASE)
    (tmp_path / "imp.py").write_text(f"import datetime\nfrom base import *\nCONFIG = [Base([{rows}])]\n")
    return runner.invoke(
        app,
        [*args, "--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "bank.txt")]
        + ["--config", str(tmp_path / "imp.py")],
    )


UNBALANCED = ", ".join(f'txn(day({n}), "r{n}", b="{"3.50" if n == 3 else "3.00"}")' for n in range(1, 6))


def test_an_unbalanced_row_is_invalid_not_ready(tmp_path: Path, bea_config_dir: Path) -> None:
    result = _import(tmp_path, UNBALANCED, "--json")

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    assert [row["status"] for row in data["rows"]] == ["new", "new", "invalid", "new", "new"]
    assert data["rows"][2]["reason"] == "Transaction does not balance: (0.50 USD)"
    assert data["rows"][2]["include"] is False
    assert data["ready"] == 4 and data["invalid"] == 1
    assert data["validation_errors"] == ["Row 3: Transaction does not balance: (0.50 USD)"]


def test_the_preview_does_not_send_an_invalid_import_to_apply(tmp_path: Path, bea_config_dir: Path) -> None:
    result = _import(tmp_path, UNBALANCED)

    assert result.exit_code == 0, result.output
    assert "4 ready, 0 exact duplicates, 0 possible duplicates, 1 invalid" in result.stdout
    assert "repeat with --apply" not in result.stdout
    assert "fix the errors above before --apply" in result.stdout


def test_apply_names_the_invalid_row(tmp_path: Path, bea_config_dir: Path) -> None:
    _import(tmp_path, UNBALANCED, "--json")
    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "bank.txt")]
        + ["--config", str(tmp_path / "imp.py"), "--apply"],
    )

    assert result.exit_code == 1, result.output
    error = json.loads(result.stderr)["error"]
    assert error["message"] == "Import would leave the ledger invalid; nothing was written."
    assert error["details"] == ["Row 3: Transaction does not balance: (0.50 USD)"]
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_apply_refuses_a_dict_metadata_value_it_would_silently_drop(tmp_path: Path, bea_config_dir: Path) -> None:
    """The printer passes over dict values, so the row printed fine and lost them (w5/728)."""
    _import(tmp_path, 'txn(day(1), "r1", meta={"ok": {"a": 1}})', "--json")
    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "bank.txt")]
        + ["--config", str(tmp_path / "imp.py"), "--apply"],
    )

    assert result.exit_code == 1, result.output
    error = json.loads(result.stderr)["error"]
    assert (
        error["message"] == "Importer base row 1 cannot be written as a ledger entry: metadata 'ok' is a dict, "
        "which Beancount cannot print."
    )
    assert (tmp_path / "main.bean").read_text() == LEDGER


@pytest.mark.parametrize(
    ("rows", "said"),
    [
        (
            'txn(day(1), "r1", account="Expenses:Dining"), txn(day(2), "r2"), '
            'txn(day(3), "r3", meta={"BankRef": "abc"}), txn(day(4), "r4")',
            "Importer base row 3 cannot be written as a ledger entry: it would be written as 0 directive(s)",
        ),
        (
            'txn(day(1), "r1"), txn("2026-02-02", "r2")',
            "Importer base row 2 cannot be written as a ledger entry: its date is a str ('2026-02-02'), "
            "not a datetime.date.",
        ),
        (
            'txn(day(1), "r1"), txn(datetime.datetime(2026, 2, 2, 10, 0), "r2")',
            "Importer base row 2 cannot be written as a ledger entry: its date is a datetime",
        ),
        (
            ", ".join(f'txn(day({n}), "r{n}", units={n != 3})' for n in range(1, 5)),
            "Importer base row 3 cannot be written as a ledger entry: its Assets:Checking posting has no amount.",
        ),
        (
            'txn(day(1), "r1", meta={"ok": {"a": 1}})',
            "Importer base row 1 cannot be written as a ledger entry: metadata 'ok' is a dict, "
            "which Beancount cannot print.",
        ),
        (
            'txn(day(1), "r1", meta={"inv": Inventory()})',
            "Importer base row 1 cannot be written as a ledger entry: metadata 'inv' is an Inventory, "
            "which Beancount cannot print.",
        ),
        (
            'txn(day(1), "r1", pmeta={"ok": {"a": 1}})',
            "Importer base row 1 cannot be written as a ledger entry: posting 2 metadata 'ok' is a dict, "
            "which Beancount cannot print.",
        ),
    ],
    ids=[
        "metadata-key",
        "string-date",
        "datetime-date",
        "no-units",
        "dict-meta",
        "inventory-meta",
        "posting-dict-meta",
    ],
)
def test_an_unwritable_row_stops_the_import_naming_it(
    tmp_path: Path, bea_config_dir: Path, rows: str, said: str
) -> None:
    result = _import(tmp_path, rows)

    assert result.exit_code == 1, result.output
    assert said in " ".join(result.stderr.split())
    assert "Directive " not in result.stderr and "Error: AttributeError" not in result.stderr
