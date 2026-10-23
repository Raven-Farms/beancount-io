"""A blocked row's "opens … after this row" names the real file or the import's row (w5/636).

When `auto_accounts` or an importer's own `open` sent import for a second
look at the ledger as the import would leave it, that load ran on staged
copies and kept their names: the reason cited `.bea-<hex>.tmp:4`, a file gone
when the command returned.
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

    class Imp:
        name = "imp"

        def identify(self, filepath):
            return True

        def account(self, filepath):
            return "Assets:Bank"

        def extract(self, filepath, existing):
            day = datetime.date(2026, 3, 1)
            opened = data.Open(data.new_metadata(filepath, 0), day, "Expenses:Dining", ["USD"], None)
            postings = [
                data.Posting("Expenses:Dining", amount.Amount(D("10.00"), "USD"), None, None, None, None),
                data.Posting("Assets:Bank", amount.Amount(D("-10.00"), "USD"), None, None, None, None),
            ]
            lunch = data.Transaction(
                data.new_metadata(filepath, 1), datetime.date(2026, 2, 1), "*", None, "Lunch",
                data.EMPTY_SET, data.EMPTY_SET, postings,
            )
            return [opened, lunch]

    CONFIG = [Imp()]
""")


def _rows(tmp_path: Path, *args: str) -> list[dict[str, Any]]:
    result = runner.invoke(app, ["--json", "--no-input", "--file", str(tmp_path / "main.bean"), "import", *args])
    assert result.exit_code == 0, result.output
    rows: list[dict[str, Any]] = json.loads(result.stdout)["data"]["rows"]
    return rows


def test_an_open_the_import_carries_is_named_by_its_row(tmp_path: Path, bea_config_dir: Path) -> None:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Bank USD\n')
    (tmp_path / "bank.txt").write_text("x\n")
    (tmp_path / "imp.py").write_text(IMPORTER)

    rows = _rows(tmp_path, str(tmp_path / "bank.txt"), "--config", str(tmp_path / "imp.py"))

    assert rows[1]["status"] == "blocked"
    assert rows[1]["reason"].startswith(
        "Account 'Expenses:Dining' opens 2026-03-01 (row 1 of this import), after this row's 2026-02-01."
    )


def test_a_ledger_open_is_named_at_its_file(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        'option "operating_currency" "USD"\nplugin "beancount.plugins.auto_accounts"\n\n'
        "2026-03-01 open Assets:Checking USD\n"
    )
    (tmp_path / "s.csv").write_text("Date,Payee,Narration,Amount\n2026-02-02,Cafe,Coffee,-5.00\n")

    (row,) = _rows(
        tmp_path,
        str(tmp_path / "s.csv"),
        "--csv",
        "date=Date,amount=Amount,payee=Payee,narration=Narration",
        "--account",
        "Assets:Checking",
        "--default-account",
        "Expenses:Misc",
    )

    assert row["status"] == "blocked"
    assert f"opens 2026-03-01 (at {ledger}:4), after this row's 2026-02-02." in row["reason"]
    assert ".bea-" not in row["reason"]


def _linked_books(tmp_path: Path, *, leaf: bool) -> Path:
    books = tmp_path / "books"
    books.mkdir()
    root = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Bank USD\n'
    (books / "main.bean").write_text(root + ('include "txns/2026.bean"\n' if leaf else ""))
    if leaf:
        (books / "txns").mkdir()
        (books / "txns" / "2026.bean").write_text("; imported rows\n")
    (books / "bank.txt").write_text("x\n")
    (books / "imp.py").write_text(IMPORTER)
    link = tmp_path / "books-link"
    link.symlink_to(books)
    return link


def test_an_open_the_import_carries_is_its_row_through_a_linked_root(tmp_path: Path, bea_config_dir: Path) -> None:
    """Through `books-link/` the reason cited `main.bean:<line>`, a line only the staged copy had (w5/856)."""
    link = _linked_books(tmp_path, leaf=False)
    before = (link / "main.bean").read_bytes()
    args = ["--json", "--no-input", "--file", str(link / "main.bean"), "import", str(link / "bank.txt")]
    args += ["--config", str(link / "imp.py")]

    preview = runner.invoke(app, args)
    applied = runner.invoke(app, [*args, "--apply"])

    assert preview.exit_code == 0, preview.output
    reason = json.loads(preview.stdout)["data"]["rows"][1]["reason"]
    assert reason.startswith("Account 'Expenses:Dining' opens 2026-03-01 (row 1 of this import), after")
    assert applied.exit_code == 4, applied.output
    assert "(row 1 of this import)" in applied.stderr and "main.bean:" not in applied.stderr
    assert (link / "main.bean").read_bytes() == before


def test_an_open_the_import_carries_is_its_row_into_a_linked_include(tmp_path: Path, bea_config_dir: Path) -> None:
    link = _linked_books(tmp_path, leaf=True)
    before = (link / "txns" / "2026.bean").read_bytes()

    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(link / "main.bean"), "import", str(link / "bank.txt")]
        + ["--config", str(link / "imp.py"), "--into", "txns/2026.bean"],
    )

    assert result.exit_code == 0, result.output
    reason = json.loads(result.stdout)["data"]["rows"][1]["reason"]
    assert "(row 1 of this import)" in reason and "2026.bean:" not in reason
    assert (link / "txns" / "2026.bean").read_bytes() == before
