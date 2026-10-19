"""Generated import ids hash the description before escaping it (w5/756).

`single_line` escapes a tab to the literal `\\x09` for the ledger, but the
digest hashed that escaped spelling: `POS<TAB>STARBUCKS` id'd as
`POS\\X09STARBUCKS`, against the documented whitespace-collapsed input — so
documented hashes and earlier-version ids missed, and re-imports needed
`--duplicates`. The canonical id now hashes the raw description, and the
0.3.1 escaped spelling stays a lookup-only key.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    'option "operating_currency" "USD"\n'
    "2020-01-01 open Assets:Checking USD\n"
    "2020-01-01 open Expenses:Uncategorized USD\n"
)
MAPPING = "date=Date,amount=Amount,narration=Description"

# The note's fixture: `2026-01-10,"POS<TAB>STARBUCKS",-9.00`.
DOCUMENTED_ID = "csv:sha256:967710cea24faf54"
ESCAPED_ID = "csv:sha256:792956864926c2e6"


def _book(tmp_path: Path) -> Path:
    file = tmp_path / "main.bean"
    file.write_text(LEDGER)
    return file


def _import(file: Path, source: Path, *args: str) -> dict[str, Any]:
    result = runner.invoke(
        app,
        ["--json", "--file", str(file), "import", str(source), "--csv", MAPPING, "--account", "Assets:Checking", *args],
    )
    assert result.exit_code == 0, result.output
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def _row_id(row: dict[str, Any]) -> str:
    found = re.search(r"csv:sha256:\w+", row["entry"])
    assert found, row["entry"]
    return found.group(0)


def test_tab_in_description_hashes_as_documented(tmp_path: Path) -> None:
    source = tmp_path / "tab.csv"
    source.write_text('Date,Description,Amount\n2026-01-10,"POS\tSTARBUCKS",-9.00\n')
    (row,) = _import(_book(tmp_path), source)["rows"]

    assert _row_id(row) == DOCUMENTED_ID


@pytest.mark.parametrize("control", ["\t", "\u202a"])
def test_control_in_description_dedupes_after_apply(tmp_path: Path, control: str) -> None:
    source = tmp_path / "tab.csv"
    source.write_text(f'Date,Description,Amount\n2026-01-10,"POS{control}STARBUCKS",-9.00\n')
    book = _book(tmp_path)
    applied = _import(book, source, "--apply")
    assert applied["written"] == 1

    again = _import(book, source)

    (row,) = again["rows"]
    assert row["status"] == "duplicate"


def test_row_written_with_the_escaped_id_still_dedupes(tmp_path: Path) -> None:
    book = _book(tmp_path)
    book.write_text(
        LEDGER + '2026-01-10 ! "POS\\\\x09STARBUCKS"\n  import-id: "csv:sha256:792956864926c2e6"\n'
        "  Assets:Checking         -9.00 USD\n  Expenses:Uncategorized\n"
    )
    check = runner.invoke(app, ["--file", str(book), "check"])
    assert check.exit_code == 0, check.output
    source = tmp_path / "tab.csv"
    source.write_text('Date,Description,Amount\n2026-01-10,"POS\tSTARBUCKS",-9.00\n')

    data = _import(book, source)

    (row,) = data["rows"]
    assert row["status"] == "duplicate"
    # The entry carries the new id while the match names the stored one:
    # the escaped spelling matched as a lookup-only key.
    assert _row_id(row) == DOCUMENTED_ID
    assert row["reason"] == f"import-id {ESCAPED_ID} is already in the ledger."


def test_second_identical_row_reproduces_its_stored_escaped_id(tmp_path: Path) -> None:
    # Occurrences number over the escaped base as 0.3.1 numbered them.
    book = _book(tmp_path)
    escaped_second = hashlib.sha256(b"2026-01-10|-9 USD|POS\\X09STARBUCKS|Assets:Checking|2").hexdigest()[:16]
    documented_second = hashlib.sha256(b"2026-01-10|-9 USD|POS STARBUCKS|Assets:Checking|2").hexdigest()[:16]
    book.write_text(
        LEDGER + '2026-01-10 ! "POS\\\\x09STARBUCKS"\n  import-id: "csv:sha256:792956864926c2e6"\n'
        "  Assets:Checking         -9.00 USD\n  Expenses:Uncategorized\n"
        '2026-01-10 ! "POS\\\\x09STARBUCKS"\n  import-id: "csv:sha256:' + escaped_second + '"\n'
        "  Assets:Checking         -9.00 USD\n  Expenses:Uncategorized\n"
    )
    source = tmp_path / "tab.csv"
    source.write_text('Date,Description,Amount\n2026-01-10,"POS\tSTARBUCKS",-9.00\n2026-01-10,"POS\tSTARBUCKS",-9.00\n')

    data = _import(book, source)

    assert [(row["status"], _row_id(row)) for row in data["rows"]] == [
        ("duplicate", DOCUMENTED_ID),
        ("duplicate", f"csv:sha256:{documented_second}"),
    ]
    assert data["rows"][0]["reason"] == f"import-id {ESCAPED_ID} is already in the ledger."
    assert data["rows"][1]["reason"] == f"import-id csv:sha256:{escaped_second} is already in the ledger."


def test_tab_in_payee_hashes_both_as_documented(tmp_path: Path) -> None:
    source = tmp_path / "payee.csv"
    source.write_text('Date,Payee,Description,Amount\n2026-01-10,"STAR\tBUCKS",Card purchase,-9.00\n')
    result = runner.invoke(
        app,
        [
            "--json",
            "--file",
            str(_book(tmp_path)),
            "import",
            str(source),
            "--csv",
            "date=Date,amount=Amount,payee=Payee,narration=Description",
            "--account",
            "Assets:Checking",
        ],
    )
    assert result.exit_code == 0, result.output
    (row,) = json.loads(result.stdout)["data"]["rows"]

    assert _row_id(row) == "csv:sha256:77c08a8f0eccce1e"
