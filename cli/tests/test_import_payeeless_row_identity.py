"""A row with no payee keeps its own id beside payee-bearing rows (w5/140).

`STARBUCKS / CARD PURCHASE -5.00` and a blank-payee `CARD PURCHASE -5.00` on
one day share a narration-only base. The blank-payee row was numbered among
the payee-bearing rows too, so behind STARBUCKS it became occurrence 2 and no
longer matched the id the ledger held for it — while STARBUCKS, looking for an
id an earlier release might have written, took that stored entry instead.
STARBUCKS was an exact duplicate and `--duplicates skip --apply` dropped it.

Rows with one description are now numbered among themselves, and a stored
narration-only id whose entry has no payee goes to a row with no payee first.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Uncategorized USD
"""
HEADER = "Date,Payee,Description,Amount\n"
STARBUCKS = "2026-02-01,STARBUCKS,CARD PURCHASE,-5.00\n"
BLANK = "2026-02-01,,CARD PURCHASE,-5.00\n"
MAPPING = "date=Date,payee=Payee,narration=Description,amount=Amount"
NARRATION_ONLY = "2026-02-01|-5 USD|CARD PURCHASE|Assets:Checking"
PAIRED = "2026-02-01|-5 USD|STARBUCKS|CARD PURCHASE|Assets:Checking"


def _digest(base: str, occurrence: int = 1) -> str:
    text = base if occurrence == 1 else f"{base}|{occurrence}"
    return "csv:sha256:" + hashlib.sha256(text.encode()).hexdigest()[:16]


@pytest.fixture
def ledger(tmp_path: Path, bea_config_dir: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    return path


def _stored(ledger: Path, payee: str | None, import_id: str) -> None:
    """An entry as an earlier release wrote it."""
    names = f'"{payee}" "CARD PURCHASE"' if payee else '"CARD PURCHASE"'
    with ledger.open("a") as stream:
        stream.write(
            f'\n2026-02-01 * {names}\n  import-id: "{import_id}"\n'
            "  Assets:Checking  -5.00 USD\n  Expenses:Uncategorized  5.00 USD\n"
        )


def _argv(ledger: Path, rows: str, *extra: str) -> list[str]:
    source = ledger.parent / "bank.csv"
    source.write_text(HEADER + rows)
    return ["--file", str(ledger), "import", str(source), "--csv", MAPPING, "--account", "Assets:Checking", *extra]


def _import(ledger: Path, rows: str, *extra: str) -> tuple[int, dict[str, Any]]:
    result = CliRunner().invoke(app, ["--json", "--no-input", *_argv(ledger, rows, *extra)])
    if result.exit_code == 0:
        return 0, json.loads(result.stdout)["data"]
    return result.exit_code, json.loads(result.stderr)["error"].get("result") or {}


def _statuses(data: dict[str, Any]) -> list[tuple[str | None, str]]:
    return [(row["payee"] or None, row["status"]) for row in data["rows"]]


@pytest.mark.parametrize("policy", ["review", "skip", "include"])
def test_a_payee_row_ahead_of_the_stored_payeeless_row_is_new(ledger: Path, policy: str) -> None:
    assert _import(ledger, BLANK, "--apply")[0] == 0
    assert _digest(NARRATION_ONLY) in ledger.read_text()

    code, data = _import(ledger, STARBUCKS + BLANK, "--duplicates", policy, "--apply")

    assert code == 0
    assert _statuses(data) == [("STARBUCKS", "new"), (None, "duplicate")]
    assert _digest(NARRATION_ONLY) in data["rows"][1]["reason"]
    assert data["written"] == 1
    text = ledger.read_text()
    assert text.count('"STARBUCKS"') == 1
    assert text.count('"CARD PURCHASE"') == 2
    assert text.count(_digest(PAIRED)) == 1
    assert text.count(_digest(NARRATION_ONLY)) == 1


def test_the_payeeless_row_first_is_unchanged(ledger: Path) -> None:
    assert _import(ledger, BLANK, "--apply")[0] == 0

    code, data = _import(ledger, BLANK + STARBUCKS, "--duplicates", "skip", "--apply")

    assert code == 0
    assert _statuses(data) == [(None, "duplicate"), ("STARBUCKS", "new")]
    assert ledger.read_text().count(_digest(PAIRED)) == 1


@pytest.mark.parametrize("first", [STARBUCKS + BLANK, BLANK + STARBUCKS])
@pytest.mark.parametrize("again", [STARBUCKS + BLANK, BLANK + STARBUCKS])
def test_reimporting_either_order_skips_both_rows(ledger: Path, first: str, again: str) -> None:
    assert _import(ledger, BLANK, "--apply")[0] == 0
    assert _import(ledger, first, "--duplicates", "skip", "--apply")[0] == 0
    before = ledger.read_bytes()

    code, data = _import(ledger, again, "--apply")

    assert code == 0
    assert [row["status"] for row in data["rows"]] == ["duplicate", "duplicate"]
    assert data["written"] == 0
    assert ledger.read_bytes() == before


def test_the_text_preview_counts_one_ready_row(ledger: Path) -> None:
    assert _import(ledger, BLANK, "--apply")[0] == 0

    result = CliRunner().invoke(app, ["--no-input", *_argv(ledger, STARBUCKS + BLANK)])

    assert result.exit_code == 0
    assert "1 ready, 1 exact duplicates, 0 possible duplicates" in result.stdout


@pytest.mark.parametrize("rows", [STARBUCKS + BLANK, BLANK + STARBUCKS])
def test_a_payeeless_row_is_numbered_apart_from_payee_rows(ledger: Path, rows: str) -> None:
    """Its id does not depend on what precedes it, so the row alone still matches."""
    assert _import(ledger, rows, "--apply")[0] == 0
    assert _digest(NARRATION_ONLY) in ledger.read_text()
    before = ledger.read_bytes()

    code, data = _import(ledger, BLANK, "--apply")

    assert code == 0
    assert _statuses(data) == [(None, "duplicate")]
    assert ledger.read_bytes() == before


def test_identical_payeeless_rows_still_take_occurrence_suffixes(ledger: Path) -> None:
    code, _ = _import(ledger, BLANK + STARBUCKS + BLANK, "--apply", "--duplicates", "include")
    assert code == 0
    text = ledger.read_text()
    assert _digest(NARRATION_ONLY, 1) in text and _digest(NARRATION_ONLY, 2) in text

    code, data = _import(ledger, BLANK + BLANK + BLANK + STARBUCKS, "--apply", "--duplicates", "include")
    assert code == 0
    assert [row["status"] for row in data["rows"]] == ["duplicate", "duplicate", "possible_duplicate", "duplicate"]
    assert _digest(NARRATION_ONLY, 3) in ledger.read_text()


@pytest.mark.parametrize("rows", [STARBUCKS + BLANK, BLANK + STARBUCKS])
def test_an_id_numbered_behind_a_payee_row_still_matches(ledger: Path, rows: str) -> None:
    """A release that counted the payee row too wrote occurrence 2 for the blank one."""
    _stored(ledger, "STARBUCKS", _digest(PAIRED))
    _stored(ledger, None, _digest(NARRATION_ONLY, 2))
    before = ledger.read_bytes()

    code, data = _import(ledger, rows, "--apply")

    assert code == 0
    assert [row["status"] for row in data["rows"]] == ["duplicate", "duplicate"]
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("rows", [STARBUCKS + BLANK, BLANK + STARBUCKS])
def test_a_narration_only_id_stored_for_a_payee_stays_with_that_payee(ledger: Path, rows: str) -> None:
    """Written before payees were hashed: the blank row's own id spells it, and must not take it."""
    _stored(ledger, "STARBUCKS", _digest(NARRATION_ONLY))

    code, data = _import(ledger, rows, "--apply")

    assert code == 0
    assert sorted(_statuses(data), key=str) == [("STARBUCKS", "duplicate"), (None, "new")]
    assert ledger.read_text().count('"STARBUCKS"') == 1
