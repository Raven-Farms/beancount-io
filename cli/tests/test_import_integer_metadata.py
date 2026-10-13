"""A Python importer's integer metadata is written as a number (w5/227).

An importer builds entries in Python, where `check_number=1042` is an `int`.
Beancount's printer writes only `Decimal` numbers, so preview and apply failed
with `ValueError: Unexpected value: '1042'`, naming neither the importer nor
the row. A value that still cannot be printed now says which row returned it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Expenses:Food\n"
    "2026-01-01 open Equity:Opening\n"
    "\n"
    '2026-01-02 * "Opening balance"\n'
    "  Assets:Checking  1000.00 USD\n"
    "  Equity:Opening\n"
)

IMPORTER = textwrap.dedent("""
    import datetime
    from decimal import Decimal as D

    from beancount.core import data
    from beancount.core.amount import Amount


    def txn(filepath, day=5, posting_meta=None, **meta):
        return data.Transaction(
            dict(data.new_metadata(filepath, 1), **meta), datetime.date(2026, 1, day), "*", "Cafe", "Coffee",
            frozenset(), frozenset(),
            [
                data.Posting("Assets:Checking", Amount(D("-5.25"), "USD"), None, None, None, posting_meta),
                data.Posting("Expenses:Food", Amount(D("5.25"), "USD"), None, None, None, None),
            ],
        )


    class Imp:
        name = "demo"

        def identify(self, filepath):
            return True

        def account(self, filepath):
            return "Assets:Checking"

        def extract(self, filepath, existing):
            case = filepath.rsplit("/", 1)[-1].removesuffix(".txt")
            if case == "integer":
                return [txn(filepath, check_number=1042)]
            if case == "decimal":
                return [txn(filepath, check_number=D("1042"))]
            if case == "posting":
                return [txn(filepath, posting_meta={"sequence": -7}, cleared=True)]
            if case == "bank":
                return [txn(filepath, bank_id=77)]
            print("row two is the bad one")
            good = txn(filepath, day=4)
            if case == "float":
                return [good, txn(filepath, rate=1.5)]
            if case == "object":
                return [good, txn(filepath, raw=object())]
            if case == "custom":
                custom = data.Custom(
                    data.new_metadata(filepath, 2), datetime.date(2026, 1, 5), "budget", [("monthly", str)]
                )
                return [good, custom]
            raise AssertionError(case)


    CONFIG = [Imp()]
""")


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _books(tmp_path: Path, case: str) -> tuple[Path, list[str]]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    config = tmp_path / "importers.py"
    config.write_text(IMPORTER, encoding="utf-8")
    source = tmp_path / f"{case}.txt"
    source.write_text("statement\n", encoding="utf-8")
    return ledger, ["--file", str(ledger), "import", str(source), "--config", str(config)]


@pytest.mark.parametrize("case", ["integer", "decimal"])
def test_integer_metadata_is_written_as_a_number(tmp_path: Path, case: str) -> None:
    """The note's fixture and its `Decimal` control write the same line."""
    ledger, argv = _books(tmp_path, case)

    preview = _bea(tmp_path, *argv)
    assert preview.returncode == 0, preview.stderr
    assert "+  check_number: 1042\n" in preview.stdout
    assert ledger.read_text(encoding="utf-8") == LEDGER

    done = _bea(tmp_path, *argv, "--apply")
    assert done.returncode == 0, done.stderr
    assert "  check_number: 1042\n" in ledger.read_text(encoding="utf-8")

    check = _bea(tmp_path, "--file", str(ledger), "check")
    assert check.returncode == 0, check.stdout + check.stderr


def test_posting_integer_metadata_is_written_and_a_boolean_stays_a_boolean(tmp_path: Path) -> None:
    ledger, argv = _books(tmp_path, "posting")

    done = _bea(tmp_path, *argv, "--apply")

    assert done.returncode == 0, done.stderr
    written = ledger.read_text(encoding="utf-8")
    assert "    sequence: -7\n" in written
    assert "  cleared: TRUE\n" in written


def test_integer_bank_id_deduplicates_on_the_second_import(tmp_path: Path) -> None:
    ledger, argv = _books(tmp_path, "bank")

    first = _bea(tmp_path, "--json", *argv, "--apply")
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["data"]["written"] == 1
    written = ledger.read_text(encoding="utf-8")
    assert '  bank_id: 77\n  import-id: "bank:77"\n' in written

    again = _bea(tmp_path, "--json", *argv, "--apply")
    assert again.returncode == 0, again.stderr
    answer = json.loads(again.stdout)["data"]
    assert (answer["written"], answer["duplicates"]) == (0, 1)
    assert ledger.read_text(encoding="utf-8") == written


@pytest.mark.parametrize(
    ("case", "cause"),
    [
        ("float", "(ValueError): Unexpected value: '1.5'."),
        ("object", "(ValueError): Unexpected value: '<object object at "),
        ("custom", "(AttributeError): 'tuple' object has no attribute "),
    ],
)
def test_unprintable_row_names_the_importer_and_the_row(tmp_path: Path, case: str, cause: str) -> None:
    ledger, argv = _books(tmp_path, case)

    done = _bea(tmp_path, *argv, "--apply")
    assert done.returncode == 1, done.stderr
    assert done.stdout == ""
    assert "Error: Importer demo row 2 cannot be written as a ledger entry " + cause in done.stderr
    assert "Traceback" not in done.stderr
    assert ledger.read_text(encoding="utf-8") == LEDGER

    structured = _bea(tmp_path, "--json", *argv, "--apply")
    assert structured.returncode == 1, structured.stderr
    error = json.loads(structured.stderr)["error"]
    assert error["category"] == "validation"
    assert error["message"].startswith("Importer demo row 2 cannot be written as a ledger entry " + cause)
    assert "row two is the bad one" in error["result"]["importer_output"]
    assert ledger.read_text(encoding="utf-8") == LEDGER
