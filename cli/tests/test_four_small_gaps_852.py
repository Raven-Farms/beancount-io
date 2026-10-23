"""Four small gaps after w5/631, 634, 630 and 633 (w5/852).

`--search` could not find the blanks the table shows around a narration's line
break; any `sys.exit` in an importer method got the "unguarded
beangulp.Ingest(CONFIG)()" hint; `price export -oDIR` was refused; and a
posting's own `filename:` read as "Duplicate posting metadata field".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
OPENS = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Rent USD\n'


def _bea(*args: str) -> object:
    return runner.invoke(app, ["--no-input", *args])


@pytest.mark.parametrize("term", ["Rent   for February", "rent for february", "RENT\tFOR  FEBRUARY"])
def test_search_finds_the_narration_as_the_table_shows_it(tmp_path: Path, term: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(OPENS + '2024-01-07 * "Landlord" "Rent\n  for February"\n  Expenses:Rent  5 USD\n  Assets:Cash\n')

    result = runner.invoke(app, ["--json", "--file", str(ledger), "list", "transaction", "--search", term])

    assert result.exit_code == 0, result.output
    assert [row["payee"] for row in json.loads(result.stdout)["data"]] == ["Landlord"]


IMPORTER = """
import datetime, sys
from decimal import Decimal as D
from beancount.core import amount, data

class Bank:
    name = "bank"
    def identify(self, filepath):
        {identify}
    def account(self, filepath):
        return "Assets:Cash"
    def extract(self, filepath, existing):
        legs = [data.Posting(a, amount.Amount(D(n), "USD"), None, None, None, None)
                for a, n in (("Assets:Cash", "-5"), ("Expenses:Rent", "5"))]
        return [data.Transaction(data.new_metadata("b", 1), datetime.date(2024, 2, 1), "*", None, "x",
                                 data.EMPTY_SET, data.EMPTY_SET, legs)]

{tail}
"""


@pytest.mark.parametrize(
    ("identify", "tail", "said", "not_said"),
    [
        (
            'sys.exit("unsupported export")',
            "CONFIG = [Bank()]",
            "Importer bank identify() called sys.exit (unsupported export); an importer method must return",
            "Ingest(CONFIG)",
        ),
        (
            "return True",
            'CONFIG = [Bank()]\nsys.exit("ingest")',
            "as an unguarded beangulp.Ingest(CONFIG)() does",
            None,
        ),
    ],
    ids=["method", "module"],
)
def test_a_sys_exit_is_named_where_it_happened(
    tmp_path: Path, identify: str, tail: str, said: str, not_said: str | None
) -> None:
    (tmp_path / "main.bean").write_text(OPENS)
    (tmp_path / "bank.txt").write_text("x\n")
    (tmp_path / "imp.py").write_text(IMPORTER.format(identify=identify, tail=tail))

    result = _bea(
        "--file",
        str(tmp_path / "main.bean"),
        "import",
        str(tmp_path / "bank.txt"),
        "--config",
        str(tmp_path / "imp.py"),
    )

    text = " ".join(result.output.split())  # type: ignore[attr-defined]
    assert result.exit_code == 1, text  # type: ignore[attr-defined]
    assert said in text
    if not_said is not None:
        assert not_said not in text


def test_price_export_accepts_an_attached_output(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(OPENS)

    result = _bea("--file", str(ledger), "price", "export", f"-o{tmp_path / 'exp'}")

    assert result.exit_code == 0, result.output  # type: ignore[attr-defined]
    assert (tmp_path / "exp" / "main.bean").read_text() == OPENS


def test_a_posting_filename_key_is_reported_as_reserved(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        OPENS + '2024-01-07 * "Rent"\n  Expenses:Rent  5 USD\n    filename: "receipt.pdf"\n  Assets:Cash\n'
    )

    result = _bea("--file", str(ledger), "list", "transaction")

    text = " ".join(result.output.split())  # type: ignore[attr-defined]
    assert f"{ledger}:5: Metadata key 'filename' is reserved for Beancount's source location" in text
    assert "Duplicate posting metadata field" not in text
