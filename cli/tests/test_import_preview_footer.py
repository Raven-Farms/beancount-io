"""Import's human preview footer describes the next action the real preview permits (w5/696)."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Uncategorized USD\n"
HEADER = ["Date", "Payee", "Description", "Amount", "ID", "Category", "Status"]
MAPPING = "date=Date,payee=Payee,narration=Description,amount=Amount,id=ID,category=Category,status=Status"
APPLY = "Preview only. Review the entries, then repeat with --apply to write."
NOTHING = "Nothing new to import."
DUPLICATES = "Preview only. Review possible duplicates and choose --duplicates skip/include, then preview again."


@pytest.fixture
def book(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _row(
    *,
    identifier: str = "bank-1",
    amount: str = "-5.00",
    narration: str = "Coffee",
    payee: str = "Cafe",
    category: str = "",
    status: str = "Posted",
) -> list[str]:
    return ["2026-09-02", payee, narration, amount, identifier, category, status]


def _source(book: Path, rows: list[list[str]], *, blank: bool = False) -> None:
    with (book.parent / "statement.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADER)
        writer.writerows(rows)
        if blank:
            writer.writerow([""] * len(HEADER))


def _import(
    book: Path, *args: str, as_json: bool = False, importer: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(book.parent / "config"),
        XDG_CACHE_HOME=str(book.parent / "cache"),
        XDG_DATA_HOME=str(book.parent / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    how = ["--config", str(importer)] if importer else ["--csv", MAPPING, "--account", "Assets:Checking"]
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            *(["--json"] if as_json else []),
            "--no-input",
            "--file",
            str(book),
            "import",
            str(book.parent / "statement.csv"),
            *how,
            *args,
        ],
        env=env,
        cwd=book.parent,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _data(done: subprocess.CompletedProcess[str], code: int = 0) -> dict[str, Any]:
    assert done.returncode == code, done.stdout + done.stderr
    if code:
        assert done.stdout == ""
        return dict(json.loads(done.stderr)["error"]["result"])
    return dict(json.loads(done.stdout)["data"])


def _preview(book: Path, footer: str, *args: str, importer: Path | None = None) -> dict[str, Any]:
    before = book.read_bytes()

    human = _import(book, *args, importer=importer)

    assert human.returncode == 0, human.stdout + human.stderr
    assert human.stdout.rstrip().splitlines()[-1] == footer, human.stdout + human.stderr
    machine = _import(book, *args, as_json=True, importer=importer)
    data = _data(machine)
    assert "Preview only." not in machine.stdout and NOTHING not in machine.stdout
    assert book.read_bytes() == before
    return data


def _seed(book: Path) -> None:
    _source(book, [_row()])
    assert _data(_import(book, "--apply", as_json=True))["written"] == 1


def test_an_exact_duplicate_after_a_real_apply_has_nothing_to_import(book: Path) -> None:
    _seed(book)
    before = book.read_bytes()

    preview = _preview(book, NOTHING)

    assert preview["ready"] == 0 and preview["duplicates"] == 1
    assert preview["blocked"] == preview["conflicts"] == 0
    applied = _data(_import(book, "--apply", as_json=True))
    assert applied["written"] == 0 and book.read_bytes() == before


@pytest.mark.parametrize("has_ready", [False, True], ids=["all-blocked", "mixed-ready-blocked"])
def test_blocked_accounts_require_repair_even_when_other_rows_are_ready(book: Path, has_ready: bool) -> None:
    if has_ready:
        book.write_text(LEDGER + "2027-01-01 open Expenses:Late USD\n")
        rows = [_row(category="Expenses:Late")]
        rows.append(_row(identifier="ready-2", amount="-9", payee="Bookshop", narration="Book"))
    else:
        book.write_text(LEDGER.replace("2026-01-01", "2026-10-17"))
        rows = [_row()]
    _source(book, rows)
    before = book.read_bytes()

    preview = _preview(book, "Preview only. Resolve the blocked rows, then preview again.")

    assert preview["blocked"] == 1 and preview["ready"] == int(has_ready)
    assert preview["conflicts"] == 0
    assert _data(_import(book, "--apply", as_json=True), 4)["written"] == 0
    assert book.read_bytes() == before


@pytest.mark.parametrize("has_ready", [False, True], ids=["all-conflicting", "mixed-ready-conflicting"])
def test_conflicting_ids_require_review_even_when_other_rows_are_ready(book: Path, has_ready: bool) -> None:
    _seed(book)
    rows = [_row(amount="-6")]
    if has_ready:
        rows.append(_row(identifier="ready-2", amount="-9", payee="Bookshop", narration="Book"))
    _source(book, rows)
    before = book.read_bytes()

    preview = _preview(book, "Preview only. Resolve the conflicting rows, then preview again.")

    assert preview["conflicts"] == 1 and preview["ready"] == int(has_ready)
    assert preview["blocked"] == 0
    assert _data(_import(book, "--apply", as_json=True), 4)["written"] == 0
    assert book.read_bytes() == before


def test_a_preview_with_both_blocked_and_conflicting_rows_names_both_before_apply(book: Path) -> None:
    _seed(book)
    book.write_text(book.read_text() + "2027-01-01 open Expenses:Late USD\n")
    _source(
        book,
        [
            _row(amount="-6"),
            _row(identifier="blocked-2", amount="-8", payee="Future", category="Expenses:Late"),
            _row(identifier="ready-3", amount="-9", payee="Bookshop", narration="Book"),
        ],
    )
    before = book.read_bytes()

    preview = _preview(book, "Preview only. Resolve the blocked and conflicting rows, then preview again.")

    assert preview["ready"] == preview["blocked"] == preview["conflicts"] == 1
    assert _data(_import(book, "--apply", as_json=True), 4)["written"] == 0
    assert book.read_bytes() == before


@pytest.mark.parametrize("policy", ["review", "skip", "include"])
@pytest.mark.parametrize("has_ready", [False, True], ids=["only-possible-duplicate", "with-ready-row"])
def test_possible_duplicate_footer_respects_the_actual_duplicate_decision(
    book: Path, policy: str, has_ready: bool
) -> None:
    _seed(book)
    rows = [_row(identifier="", narration="Posted purchase")]
    if has_ready:
        rows.append(_row(identifier="ready-2", amount="-9", payee="Bookshop", narration="Book"))
    _source(book, rows)
    before = book.read_bytes()
    expected_ready = int(has_ready) + int(policy == "include")
    expected_footer = DUPLICATES if policy == "review" else APPLY if expected_ready else NOTHING

    preview = _preview(book, expected_footer, "--duplicates", policy)

    assert preview["possible_duplicates"] == 1 and preview["ready"] == expected_ready
    assert preview["blocked"] == preview["conflicts"] == 0
    applied = _data(_import(book, "--duplicates", policy, "--apply", as_json=True), 4 if policy == "review" else 0)
    assert applied["written"] == (0 if policy == "review" else expected_ready)
    assert (book.read_bytes() != before) == bool(policy != "review" and expected_ready)


@pytest.mark.parametrize("kind", ["header-only", "blank-row", "pending-only"])
def test_an_export_with_no_ready_rows_has_no_apply_offer(book: Path, kind: str) -> None:
    _source(book, [_row(status="Pending")] if kind == "pending-only" else [], blank=kind == "blank-row")

    preview = _preview(book, NOTHING)

    assert preview["ready"] == preview["written"] == preview["blocked"] == preview["conflicts"] == 0
    if kind == "pending-only":
        assert preview["skipped_pending"] == 1
    elif kind == "blank-row":
        assert preview["skipped_blank"] == 1


def test_a_clean_ready_preview_keeps_the_apply_offer_and_apply_writes(book: Path) -> None:
    _source(book, [_row()])

    preview = _preview(book, APPLY)

    assert preview["ready"] == 1 and preview["blocked"] == preview["conflicts"] == 0
    applied = _import(book, "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert applied.stdout.rstrip().endswith(f"Wrote 1 entry to {book}.")
    assert "Preview only." not in applied.stdout
    assert "Coffee" in book.read_text()


def test_invalid_importer_entries_keep_the_validation_footer_ahead_of_empty_ready(book: Path) -> None:
    _source(book, [_row()])
    importer = book.parent / "unbalanced.py"
    importer.write_text("""import datetime
from decimal import Decimal
from beancount.core import amount, data

class Bank:
    name = "unbalanced"
    def identify(self, filepath):
        return True
    def account(self, filepath):
        return "Assets:Checking"
    def extract(self, filepath, existing):
        return [data.Transaction(data.new_metadata(filepath, 2), datetime.date(2026, 9, 2),
            "*", "Cafe", "Unbalanced", frozenset(), frozenset(), [
                data.Posting("Assets:Checking", amount.Amount(Decimal("-5"), "USD"), None, None, None, None),
                data.Posting("Expenses:Uncategorized", amount.Amount(Decimal("4"), "USD"), None, None, None, None)])]
CONFIG = [Bank()]
""")
    before = book.read_bytes()

    preview = _preview(
        book,
        "Preview only. The import would leave the ledger invalid; fix the errors above before --apply.",
        importer=importer,
    )

    assert preview["ready"] == 0 and preview["invalid"] == 1 and preview["validation_errors"]
    assert _data(_import(book, "--apply", as_json=True, importer=importer), 1)["written"] == 0
    assert book.read_bytes() == before
