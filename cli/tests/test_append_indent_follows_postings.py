"""Appends take their posting indent from postings, so a formatted file stays formatted (w5/231).

The append path guessed the file's posting indent from every indented line.
`bea`'s own four-space posting-metadata lines outvoted the two-space postings
they sat under, so the next entry was written with four-space postings and
`format --check` failed. In a tab-indented file upstream's aligner settled on
the most frequent indent *length*, and a tab is one character long, so new
postings got a single space.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
CONFIG = Path(__file__).resolve().parents[1] / "docs/examples/csv_importers.py"
# One pair of accounts throughout, so no append is wider than the lines before
# it: a wider one leaves the *older* lines for `bea format` to realign.
OPENS = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Dining USD\n'
COFFEE = ["add", "transaction", "Coffee", "--date", "2026-02-02", "-p", "Expenses:Dining 4.50 USD"]
CSV = "Date,Payee,Narration,Amount,Currency,Category,BankID\n2026-02-03,Cafe,Tea,-5.25,USD,Expenses:Dining,bank-001\n"
DINNER = ["  Expenses:Dining  12.50 USD", '    receipt: "R-1"', "  Assets:Checking", '    note: "wallet"']


def _row(date: str, narration: str, *, posting_meta: bool) -> dict[str, object]:
    spent: dict[str, object] = {"account": "Expenses:Dining", "amount": "12.50 USD"}
    paid: dict[str, object] = {"account": "Assets:Checking"}
    row: dict[str, object] = {"date": date, "narration": narration, "postings": [spent, paid]}
    if posting_meta:
        spent["meta"] = {"receipt": "R-1"}
        paid["meta"] = {"note": "wallet"}
    else:
        row["meta"] = {"receipt": "R-1", "note": "wallet"}
    return row


def _bea(ledger: Path, *args: str, stdin: str | None = None) -> None:
    result = runner.invoke(app, ["--file", str(ledger), *args], input=stdin)
    assert result.exit_code == 0, result.output


def _bulk(ledger: Path, row: dict[str, object]) -> None:
    _bea(ledger, "add", "transactions", "--from", "-", stdin=json.dumps([row]))


def _formatted(ledger: Path) -> bool:
    return runner.invoke(app, ["format", "--check", str(ledger)]).exit_code == 0


def _entry(ledger: Path, narration: str) -> list[str]:
    """The indented lines of the transaction with this narration."""
    lines = ledger.read_text().splitlines()
    start = next(index for index, line in enumerate(lines) if f'"{narration}"' in line) + 1
    stop = next((index for index in range(start, len(lines)) if not lines[index].startswith((" ", "\t"))), len(lines))
    return lines[start:stop]


def _two_space(lines: list[str]) -> bool:
    return bool(lines) and all(line.startswith("  ") and line[2] != " " for line in lines)


@pytest.mark.parametrize("posting_meta", [True, False], ids=["posting-meta", "transaction-meta-control"])
def test_add_after_a_bulk_row_keeps_two_space_postings(tmp_path: Path, posting_meta: bool) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(OPENS)
    _bulk(ledger, _row("2026-02-01", "Lunch", posting_meta=posting_meta))
    assert _formatted(ledger)

    _bea(ledger, *COFFEE, "-p", "Assets:Checking")

    assert _entry(ledger, "Coffee") == ["  Expenses:Dining   4.50 USD", "  Assets:Checking"]
    assert _formatted(ledger)


def test_bulk_and_import_after_posting_metadata_stay_formatted(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(OPENS)
    _bulk(ledger, _row("2026-02-01", "Lunch", posting_meta=True))

    _bulk(ledger, _row("2026-02-02", "Dinner", posting_meta=True))
    assert _entry(ledger, "Dinner") == DINNER
    assert _formatted(ledger)

    source = tmp_path / "bank.csv"
    source.write_text(CSV)
    preview = runner.invoke(app, ["--json", "--file", str(ledger), "import", str(source), "--config", str(CONFIG)])
    assert preview.exit_code == 0, preview.output
    diff = json.loads(preview.stdout)["data"]["diff"]
    assert _two_space([line[1:] for line in diff.splitlines() if line.startswith("+ ")]), diff
    _bea(ledger, "import", str(source), "--config", str(CONFIG), "--apply")
    assert _two_space(_entry(ledger, "Tea"))
    assert _formatted(ledger)


@pytest.mark.parametrize("indent", ["\t", "  "], ids=["tab", "two-space-control"])
def test_appends_to_a_tab_indented_ledger_write_two_space_postings(tmp_path: Path, indent: str) -> None:
    ledger = tmp_path / "main.bean"
    original = OPENS + (
        f'\n2026-01-02 * "a"\n{indent}Expenses:Dining  1.00 USD\n{indent}Assets:Checking\n'
        f'\n2026-01-03 * "b"\n{indent}Expenses:Dining  2.00 USD\n{indent}Assets:Checking\n'
    )
    ledger.write_text(original)

    _bea(ledger, *COFFEE, "-p", "Assets:Checking")

    assert _entry(ledger, "Coffee") == ["  Expenses:Dining  4.50 USD", "  Assets:Checking"]
    written = ledger.read_text()
    assert written.startswith(original), "existing lines are never rewritten"
    # The appended lines already sit where `bea format` puts them: formatting
    # the file rewrites only the older, tab-indented entries.
    copy = tmp_path / "copy.bean"
    copy.write_text(written)
    _bea(copy, "format", "-i", str(copy))
    assert copy.read_text().endswith(written[len(original) :])
    assert _formatted(ledger) is (indent == "  ")

    _bulk(ledger, _row("2026-02-04", "Dinner", posting_meta=True))
    source = tmp_path / "bank.csv"
    source.write_text(CSV)
    _bea(ledger, "import", str(source), "--config", str(CONFIG), "--apply")

    assert _entry(ledger, "Dinner") == DINNER
    assert _two_space(_entry(ledger, "Tea"))
    assert ledger.read_text().startswith(original)
