"""Metadata named `filename:` or `lineno:` is an error, and never moves the entry (w5/630).

Beancount fills both keys with where a directive is written, then merges the
directive's own metadata, or a `pushmeta`, over them without a word. With
`filename: "scan-0042.pdf"` on a receipt, `list --on-disk` hid the entry,
`list` called it generated, `import` and `add balance` wrote it again, and a
date-valued `filename:` failed every `list` on its model. `check` passed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
OPENS = "2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n"
RECEIPT = (
    OPENS
    + '2024-01-02 * "Shop" "receipt attached"\n  filename: "scan-0042.pdf"\n'
    + "  Expenses:Food  1.00 USD\n  Assets:Cash\n"
    + '2024-01-03 * "Shop" "plain"\n  Expenses:Food  2.00 USD\n  Assets:Cash\n'
)
RESERVED = "Metadata key '{}' is reserved for Beancount's source location; choose another key."


def _ledger(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "a.bean"
    path.write_text(text)
    return path


@pytest.mark.parametrize(
    ("text", "line", "key"),
    [
        (RECEIPT, 3, "filename"),
        (
            OPENS + 'pushmeta filename: "scan.pdf"\n2024-01-02 * "Shop"\n  Expenses:Food  1.00 USD\n'
            "  Assets:Cash\npopmeta filename:\n",
            3,
            "filename",
        ),
        (OPENS + "2024-01-03 balance Assets:Cash 0.00 USD\n  lineno: 4.5\n", 3, "lineno"),
    ],
    ids=["entry-metadata", "pushmeta", "balance-lineno"],
)
@pytest.mark.parametrize("flags", [[], ["--debug"], ["--json"]], ids=["text", "debug", "json"])
def test_check_reports_the_reserved_key(tmp_path: Path, text: str, line: int, key: str, flags: list[str]) -> None:
    ledger = _ledger(tmp_path, text)

    result = runner.invoke(app, [*flags, "--file", str(ledger), "check"])

    assert result.exit_code == 1, result.output
    assert f"{ledger}:{line}: {RESERVED.format(key)}" in result.output


def test_another_key_still_checks_clean(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, RECEIPT.replace("filename:", "receipt:"))

    result = runner.invoke(app, ["--file", str(ledger), "check"])

    assert result.exit_code == 0, result.output


def _listed(ledger: Path, *args: str) -> list[dict[str, Any]]:
    result = runner.invoke(app, ["--json", "--file", str(ledger), "list", "transaction", "--allow-errors", *args])
    assert result.exit_code == 0, result.output
    rows: list[dict[str, Any]] = json.loads(result.stdout)["data"]
    return rows


def test_the_entry_keeps_its_location_and_stays_on_disk(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, RECEIPT)

    (receipt,) = [row for row in _listed(ledger) if row["narration"] == "receipt attached"]
    assert receipt["source"] == {"filename": str(ledger), "lineno": 3}
    assert not receipt.get("generated")
    assert {row["narration"] for row in _listed(ledger, "--on-disk")} == {"receipt attached", "plain"}


@pytest.mark.parametrize("value", ["2024-01-02", "TRUE", '"abc"'], ids=["date", "bool", "string-lineno"])
def test_a_value_of_any_type_does_not_crash_list(tmp_path: Path, value: str) -> None:
    key = "lineno" if value.startswith('"') else "filename"
    ledger = _ledger(tmp_path, RECEIPT.replace('filename: "scan-0042.pdf"', f"{key}: {value}"))

    (receipt,) = [row for row in _listed(ledger) if row["narration"] == "receipt attached"]
    assert receipt["source"] == {"filename": str(ledger), "lineno": 3}


def test_add_balance_sees_the_assertion_already_written(tmp_path: Path) -> None:
    text = OPENS + '2024-01-31 balance Assets:Cash 0.00 USD\n  filename: "statement-jan.pdf"\n'
    ledger = _ledger(tmp_path, text)

    result = runner.invoke(
        app,
        ["--file", str(ledger), "add", "balance", "-a", "Assets:Cash", "--amount", "0.00 USD"]
        + ["--date", "2024-01-31", "--allow-errors"],
    )

    assert result.exit_code == 0, result.output
    assert f"Balance already recorded at {ledger}:3" in result.output
    assert ledger.read_text() == text


def test_a_reimport_recognizes_the_written_entry(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = _ledger(
        tmp_path,
        'option "operating_currency" "USD"\n'
        "2026-01-01 open Liabilities:CreditCard USD\n2026-01-01 open Expenses:Uncategorized USD\n"
        '2026-10-04 ! "NETFLIX.COM"\n  filename: "bank-2024-01.csv"\n  lineno: 2\n'
        '  bank_id: "B2"\n  import-id: "bank:B2"\n'
        "  Liabilities:CreditCard  -15.49 USD\n  Expenses:Uncategorized   15.49 USD\n",
    )
    (tmp_path / "n.csv").write_text("Date,Description,Amount,ID\n10/04/2026,NETFLIX.COM,-15.49,B2\n")

    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(tmp_path / "n.csv")]
        + ["--csv", "date=Date,narration=Description,amount=Amount,id=ID", "--account", "Liabilities:CreditCard"]
        + ["--allow-errors"],
    )

    assert result.exit_code == 0, result.output
    (row,) = json.loads(result.stdout)["data"]["rows"]
    assert row["status"] == "duplicate"
