"""The separator is detected from complete CSV records (w5/922).

A quoted multiline preamble or header cell was sampled as physical lines, so
detection chose a separator from inside it, and the header remembered after a
forced separator was the wrongly detected one, failing the flag-free repeat.
"""

from __future__ import annotations

import csv
import io
import json
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
SEPARATORS = {"comma": ",", "semicolon": ";", "tab": "\t", "pipe": "|"}
BASE = ["import", "bank.csv", "--account", "Assets:Cash", "--default-account", "Expenses:Food"]
MAPPING = "date=Date,narration=Description,amount=Amount,id=Reference"


def _write(
    tmp_path: Path, delimiter: str, *, preamble: bool, rows: list[list[str]] | None = None, fresh: bool = True
) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    if preamble:
        writer.writerow(["Statement for synthetic account\n123 Example Road, Suite 1\nSample City, Region"])
    writer.writerow(["Date", "Description", "Amount", "Reference"])
    for row in rows or [["2024-02-01", "Coffee", "-4.50", "qa-1"], ["2024-02-02", "Lunch", "-6.25", "qa-2"]]:
        writer.writerow(row)
    (tmp_path / "bank.csv").write_text(buffer.getvalue(), encoding="utf-8")
    if fresh:
        (tmp_path / "main.bean").write_text(LEDGER)


def _cash(tmp_path: Path) -> Decimal:
    result = _bea(tmp_path, "query", "SELECT sum(number) WHERE account = 'Assets:Cash'")
    return Decimal(str(json.loads(result.stdout)["data"]["rows"][0][0]))


@pytest.mark.parametrize("separator", list(SEPARATORS.values()), ids=list(SEPARATORS))
def test_a_multiline_preamble_is_one_record_for_detection(tmp_path: Path, separator: str) -> None:
    _write(tmp_path, separator, preamble=True)
    mapped = [*BASE, "--csv", f"{MAPPING},skip=1"]

    assert _written(_bea(tmp_path, *mapped, "--apply")) == 2
    assert _cash(tmp_path) == Decimal("-10.75")
    assert _bea(tmp_path, "check").returncode == 0
    # The header remembered is the one read, so a flag-free repeat skips both.
    again = _bea(tmp_path, *BASE, "--apply")
    assert _written(again) == 0
    assert _cash(tmp_path) == Decimal("-10.75")


def test_an_overlapping_export_books_only_the_new_payment(tmp_path: Path) -> None:
    _write(tmp_path, ";", preamble=True)
    assert _written(_bea(tmp_path, *BASE, "--csv", f"{MAPPING},skip=1", "--apply")) == 2

    _write(
        tmp_path,
        ";",
        preamble=True,
        rows=[
            ["2024-02-01", "Coffee", "-4.50", "qa-1"],
            ["2024-02-02", "Lunch", "-6.25", "qa-2"],
            ["2024-02-03", "Tea", "-1.25", "qa-3"],
        ],
        fresh=False,
    )

    assert _written(_bea(tmp_path, *BASE, "--apply")) == 1


@pytest.mark.parametrize("separator", list(SEPARATORS.values()), ids=list(SEPARATORS))
def test_a_quoted_multiline_header_cell_does_not_hide_the_separator(tmp_path: Path, separator: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=separator, lineterminator="\n")
    writer.writerow(["Date", "Transaction\nDescription", "Amount"])
    writer.writerow(["2024-01-02", "Lunch", "-4.50"])
    (tmp_path / "bank.csv").write_text(buffer.getvalue(), encoding="utf-8")

    mapped = [*BASE, "--csv", 'date=Date,narration="Transaction\nDescription",amount=Amount']
    assert _written(_bea(tmp_path, *mapped, "--apply")) == 1
    assert _written(_bea(tmp_path, *BASE, "--apply")) == 0


def test_a_single_line_preamble_still_detects(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_text(
        "Statement for synthetic account\nDate;Description;Amount;Reference\n2024-02-01;Coffee;-4.50;qa-1\n"
    )

    assert _written(_bea(tmp_path, *BASE, "--csv", f"{MAPPING},skip=1", "--apply")) == 1
