"""A `query` directive's name and BQL are escaped when written (w5/225).

The printer's string-field table left `query` out, so a double quote or a
backslash in either string was written raw: the beancount-format export of a
valid ledger failed to reload, and an importer returning such a directive had
its whole batch refused.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from beancount import loader
from beancount.core.data import Query
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

NAME = 'cafe "north" C:\\books'
DOUBLE_QUOTED = 'SELECT account WHERE payee = "Cafe"'
SINGLE_QUOTED = "SELECT account WHERE payee = 'Cafe'"

LEDGER = r"""option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-03 query "cafe \"north\" C:\\books" "SELECT account WHERE payee = \"Cafe\""
2026-01-04 query "plain" "SELECT account WHERE payee = 'Cafe'"
"""

IMPORTER = """\
import datetime
from decimal import Decimal
from beancount.core.amount import Amount
from beancount.core.data import Posting, Query, Transaction, new_metadata


class Stored:
    name = "stored"

    def identify(self, filepath):
        return filepath.endswith(".csv")

    def account(self, filepath):
        return "Assets:Checking"

    def extract(self, filepath, existing):
        day = datetime.date(2026, 1, 5)
        with open(filepath) as stream:
            name, statement = stream.read().splitlines()
        return [
            Transaction(
                new_metadata(filepath, 1), day, "*", "Cafe", "Coffee", frozenset(), frozenset(),
                [
                    Posting("Assets:Checking", Amount(Decimal("-4.00"), "USD"), None, None, None, None),
                    Posting("Expenses:Food", Amount(Decimal("4.00"), "USD"), None, None, None, None),
                ],
            ),
            Query(new_metadata(filepath, 2), day, name, statement),
        ]


CONFIG = [Stored()]
"""


def _queries(path: Path) -> list[tuple[str, str]]:
    entries, errors, _options = loader.load_file(str(path))
    assert not errors, f"{path.name} did not load: {errors}\n{path.read_text(encoding='utf-8')}"
    return [(entry.name, entry.query_string) for entry in entries if isinstance(entry, Query)]


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    (tmp_path / "imp.py").write_text(IMPORTER, encoding="utf-8")
    assert _queries(ledger) == [(NAME, DOUBLE_QUOTED), ("plain", SINGLE_QUOTED)]
    return ledger


@pytest.mark.parametrize("to_file", [True, False], ids=["output-file", "stdout"])
def test_beancount_export_of_a_quoted_query_directive_reloads(book: Path, to_file: bool) -> None:
    before = book.read_bytes()
    exported = book.with_name("out.bean")
    output_args = ["--output", str(exported)] if to_file else []

    result = runner.invoke(app, ["--file", str(book), "query", "PRINT", "-f", "beancount", *output_args])

    assert result.exit_code == 0, result.output
    assert book.read_bytes() == before
    if not to_file:
        exported.write_text(result.stdout, encoding="utf-8")
    text = exported.read_text(encoding="utf-8")
    assert r'query "cafe \"north\" C:\\books" "SELECT account WHERE payee = \"Cafe\""' in text
    assert """query "plain" "SELECT account WHERE payee = 'Cafe'\"""" in text
    assert _queries(exported) == _queries(book)
    assert runner.invoke(app, ["--file", str(exported), "check"]).exit_code == 0


def _import(book: Path, name: str, statement: str, *args: str) -> Any:
    source = book.parent / "stored.csv"
    source.write_text(f"{name}\n{statement}\n", encoding="utf-8")
    config = str(book.parent / "imp.py")
    return runner.invoke(
        app, ["--json", "--no-input", "--file", str(book), "import", str(source), "--config", config, *args]
    )


@pytest.mark.parametrize(
    ("name", "statement"),
    [(NAME, DOUBLE_QUOTED), ("imported", DOUBLE_QUOTED), ("imported", SINGLE_QUOTED)],
    ids=["quoted-name-and-bql", "double-quoted-bql", "single-quoted-control"],
)
def test_an_importer_batch_holding_a_query_directive_applies(book: Path, name: str, statement: str) -> None:
    stored = _queries(book)

    preview = _import(book, name, statement)
    applied = _import(book, name, statement, "--apply")

    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.stdout)["data"]["ready"] == 2
    assert applied.exit_code == 0, applied.output
    assert '2026-01-05 * "Cafe" "Coffee"' in book.read_text(encoding="utf-8")
    assert _queries(book) == [*stored, (name, statement)]
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0
