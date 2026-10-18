"""`sign=ledger` stays with every file it was previewed for (w5/594).

The header's record kept one `sign_ledger_sha256`, and any explicit `--csv`
run on another file with that header replaced it. Card exports from
consecutive months share a header, so previewing September evicted August's
sign, and August's flag-free `--apply` wrote every amount flipped, exit 0,
with no note.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
MAPPING = "date=Date,amount=Amount,narration=Description"
LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Liabilities:Card USD\n"
    "2026-01-01 open Expenses:Uncategorized USD\n"
)


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "aug.csv").write_text("Date,Description,Amount\n2026-08-02,GROCERY,25.00\n")
    (tmp_path / "sep.csv").write_text("Date,Description,Amount\n2026-09-02,REFUND,-12.00\n")
    return ledger


def _import(book: Path, name: str, *args: str) -> dict[str, Any]:
    result = runner.invoke(app, ["--json", "--file", str(book), "import", str(book.parent / name), *args])
    assert result.exit_code == 0, result.output
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def _preview(book: Path, name: str, spec: str) -> str:
    (row,) = _import(book, name, "--account", "Liabilities:Card", "--csv", spec)["rows"]
    return str(row["amount"])


def _card_line(book: Path, amount: str) -> bool:
    return re.search(rf"^\s+Liabilities:Card\s+{re.escape(amount)} USD$", book.read_text(), re.MULTILINE) is not None


def test_previewing_another_file_keeps_the_first_files_sign(book: Path) -> None:
    assert _preview(book, "aug.csv", f"{MAPPING},sign=ledger") == "-25.00 USD"
    assert _preview(book, "sep.csv", MAPPING) == "-12.00 USD"

    applied = _import(book, "aug.csv", "--apply")

    (row,) = applied["rows"]
    assert row["amount"] == "-25.00 USD"
    assert applied["written"] == 1
    assert any("Re-applied sign=ledger: aug.csv is the file it was chosen for" in note for note in applied["notes"])
    assert _card_line(book, "-25.00")


def test_two_ledger_signed_months_both_replay(book: Path) -> None:
    assert _preview(book, "aug.csv", f"{MAPPING},sign=ledger") == "-25.00 USD"
    assert _preview(book, "sep.csv", f"{MAPPING},sign=ledger") == "12.00 USD"

    august = _import(book, "aug.csv", "--apply")
    september = _import(book, "sep.csv", "--apply")

    assert [row["amount"] for row in august["rows"] + september["rows"]] == ["-25.00 USD", "12.00 USD"]
    assert not any("read bank-signed" in note for note in august["notes"] + september["notes"])
    assert _card_line(book, "-25.00") and _card_line(book, "12.00")


def test_a_file_previewed_again_bank_signed_drops_only_its_own_sign(book: Path) -> None:
    _preview(book, "aug.csv", f"{MAPPING},sign=ledger")
    _preview(book, "sep.csv", f"{MAPPING},sign=ledger")
    assert _preview(book, "aug.csv", MAPPING) == "25.00 USD"

    august = _import(book, "aug.csv")
    september = _import(book, "sep.csv")

    assert [row["amount"] for row in august["rows"]] == ["25.00 USD"]
    assert any("aug.csv is read bank-signed" in note for note in august["notes"])
    assert [row["amount"] for row in september["rows"]] == ["12.00 USD"]


def test_a_record_from_before_keeps_its_one_ledger_signed_file(book: Path, bea_config_dir: Path) -> None:
    _preview(book, "aug.csv", f"{MAPPING},sign=ledger")
    (record,) = (bea_config_dir / "importers").glob("csv-*.json")
    stored = json.loads(record.read_text())
    entry = stored["sources"][0]
    (digest,) = entry.pop("sign_ledger_files")
    entry["sign_ledger_sha256"] = digest
    record.write_text(json.dumps(stored))

    applied = _import(book, "aug.csv", "--apply")

    assert [row["amount"] for row in applied["rows"]] == ["-25.00 USD"]
    assert _card_line(book, "-25.00")
