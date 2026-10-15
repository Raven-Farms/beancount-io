"""Importer prices keep one quote per commodity and day, as `add price` does (w5/302).

Import compared non-transaction directives by printed text alone. It wrote
`111.00 USD` beside a recorded `110.00 USD`, wrote `110.0 USD` as new, let a
second quote through within the same batch, and skipped a statement price
because `implicit_prices` had generated the same one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

HEADER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Broker:Cash USD
2026-01-01 open Assets:Broker:HOOL HOOL
2026-01-01 open Equity:Opening
2026-01-01 commodity HOOL
"""

IMPORTER = """\
import datetime
from decimal import Decimal
from beancount.core import amount, data


class Quotes:
    name = "quotes"

    def identify(self, filepath):
        return filepath.endswith("stmt.txt")

    def account(self, filepath):
        return "Assets:Broker"

    def extract(self, filepath, existing):
        out = []
        for line, text in enumerate(open(filepath).read().split(), start=1):
            day, number = text.split("=")
            out.append(
                data.Price(
                    data.new_metadata(filepath, line),
                    datetime.date.fromisoformat(day),
                    "HOOL",
                    amount.Amount(Decimal(number), "USD"),
                )
            )
        return out


CONFIG = [Quotes()]
"""


@pytest.fixture
def books(tmp_path: Path, bea_config_dir: Path) -> Path:
    (tmp_path / "imp.py").write_text(IMPORTER)
    return tmp_path


def _import(books: Path, ledger: str, quotes: str, *args: str) -> tuple[Any, Path]:
    path = books / "main.bean"
    path.write_text(ledger)
    (books / "stmt.txt").write_text(quotes)
    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(path), "import", str(books / "stmt.txt")]
        + ["--config", str(books / "imp.py"), *args],
    )
    return result, path


def _rows(result: Any) -> list[tuple[str, str]]:
    return [(row["status"], row["reason"]) for row in json.loads(result.stdout)["data"]["rows"]]


def test_a_conflicting_quote_and_a_duplicate_by_value_against_the_ledger(books: Path) -> None:
    ledger = HEADER + "2026-01-31 price HOOL 110.00 USD\n"
    preview, _ = _import(books, ledger, "2026-01-31=111.00 2026-01-31=110.0")
    assert preview.exit_code == 0, preview.output
    (first, why), (second, _) = _rows(preview)
    assert (first, second) == ("conflict", "duplicate")
    assert "price of 110.00 USD at " in why and "main.bean:6" in why

    applied, path = _import(books, ledger, "2026-01-31=111.00 2026-01-31=110.0", "--apply")
    assert applied.exit_code == 4, applied.output
    assert path.read_text() == ledger


def test_a_second_quote_within_one_batch_is_a_conflict(books: Path) -> None:
    applied, path = _import(books, HEADER, "2026-01-31=110.00 2026-01-31=111.00", "--apply")
    assert applied.exit_code == 4, applied.output
    assert "row 1 of this import" in applied.output
    assert path.read_text() == HEADER


def test_a_quote_implicit_prices_generates_is_still_written(books: Path) -> None:
    ledger = (
        HEADER.replace('"USD"\n', '"USD"\nplugin "beancount.plugins.implicit_prices"\n', 1)
        + '2026-01-05 * "Buy"\n  Assets:Broker:HOOL  10 HOOL {100.00 USD}\n  Assets:Broker:Cash\n'
    )
    applied, path = _import(books, ledger, "2026-01-05=100.00", "--apply")
    assert applied.exit_code == 0, applied.output
    assert "2026-01-05 price HOOL" in path.read_text()
