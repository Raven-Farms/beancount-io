"""CSV import recognizes accounts the ledger already opens in an include (w5/928).

The main file renames a root while an include keeps the English one, a valid
split ledger. The CSV account, fallback, rule and category checks knew only
the main file's roots, so already-open `Expenses:Food` was refused as a
fallback and treated as a label as a category (posted to suspense with `!`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

MAIN = 'option "name_expenses" "Aufwand"\noption "operating_currency" "USD"\ninclude "legacy.bean"\n'
LEGACY = "2024-01-01 open Assets:Cash USD\n2024-01-01 open Assets:Suspense USD\n2024-01-01 open Expenses:Food USD\n"
CSV = "date=Date,narration=Description,amount=Amount,id=Reference,category=Category"
BASE = ["import", "bank.csv", "--account", "Assets:Cash", "--into", "legacy.bean"]


def _books(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "legacy.bean").write_text(LEGACY)
    (tmp_path / "bank.csv").write_text(
        "Date,Description,Amount,Reference,Category\n2024-02-01,Coffee,-4.50,coffee-1,Expenses:Food\n"
    )


def test_an_already_open_account_is_a_valid_fallback_and_category(tmp_path: Path) -> None:
    _books(tmp_path)

    preview = _bea(tmp_path, *BASE, "--csv", CSV, "--default-account", "Expenses:Food")
    assert preview.returncode == 0, preview.stderr

    assert _written(_bea(tmp_path, *BASE, "--csv", CSV, "--default-account", "Expenses:Food", "--apply")) == 1
    written = (tmp_path / "legacy.bean").read_text()
    assert "Expenses:Food" in written and '2024-02-01 * "Coffee"' in written
    assert _bea(tmp_path, "check").returncode == 0
    assert _written(_bea(tmp_path, *BASE, "--csv", CSV, "--default-account", "Expenses:Food", "--apply")) == 0


def test_the_category_names_the_opened_account_not_a_label(tmp_path: Path) -> None:
    _books(tmp_path)

    applied = _bea(tmp_path, *BASE, "--csv", CSV, "--default-account", "Assets:Suspense", "--apply")

    assert _written(applied) == 1
    written = (tmp_path / "legacy.bean").read_text()
    assert '2024-02-01 * "Coffee"' in written and "Expenses:Food" in written
    assert "Assets:Suspense" not in written.split("Coffee")[1]


def test_a_root_the_ledger_never_opens_is_still_refused(tmp_path: Path) -> None:
    _books(tmp_path)
    before = (tmp_path / "legacy.bean").read_bytes()

    refused = _bea(tmp_path, *BASE, "--csv", CSV, "--default-account", "Foo:Food", "--apply")

    assert refused.returncode == 2, refused.stdout
    assert "Foo" in json.loads(refused.stderr)["error"]["message"]
    assert (tmp_path / "legacy.bean").read_bytes() == before


@pytest.mark.parametrize("name", ["Expenses:Unopened"])
def test_an_account_under_a_root_the_ledger_does_not_use_but_never_opened_is_refused(tmp_path: Path, name: str) -> None:
    _books(tmp_path)

    refused = _bea(tmp_path, *BASE, "--csv", CSV, "--default-account", name, "--apply")

    assert refused.returncode == 2, refused.stdout
