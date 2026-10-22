"""A `|` in a payee or narration cannot move the field boundary in a generated ID (w5/900).

The fields were joined with `|` unframed, so payee `Shop|Branch` + narration
`Purchase` and payee `Shop` + narration `Branch|Purchase` hashed alike and the
second payment was skipped as a duplicate, even under `--duplicates include`.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

LEDGER = "2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n"
MAPPING = "date=Date,amount=Amount,payee=Payee,narration=Narration"


def _import(tmp_path: Path, name: str, *flags: str) -> list[str]:
    return [
        "import", name, "--csv", MAPPING, "--account", "Assets:Cash", "--default-account", "Expenses:Food",
        "--duplicates", "include", *flags,
    ]  # fmt: skip


def _csv(tmp_path: Path, name: str, *rows: tuple[str, str]) -> None:
    body = "".join(f"2024-02-01,-10.00,{payee},{narration}\n" for payee, narration in rows)
    (tmp_path / name).write_text("Date,Amount,Payee,Narration\n" + body)


def _spent(tmp_path: Path) -> list[tuple[str, str, Decimal]]:
    result = _bea(tmp_path, "query", "SELECT payee, narration, number WHERE account = 'Assets:Cash' ORDER BY payee")
    return [(p, n, Decimal(str(v))) for p, n, v in json.loads(result.stdout)["data"]["rows"]]


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    return tmp_path


def test_two_files_with_shifted_boundaries_are_two_payments(books: Path) -> None:
    _csv(books, "a.csv", ("Shop|Branch", "Purchase"))
    _csv(books, "b.csv", ("Shop", "Branch|Purchase"))

    assert _written(_bea(books, *_import(books, "a.csv", "--apply"))) == 1
    assert _written(_bea(books, *_import(books, "b.csv", "--apply"))) == 1

    assert _spent(books) == [
        ("Shop", "Branch|Purchase", Decimal("-10.00")),
        ("Shop|Branch", "Purchase", Decimal("-10.00")),
    ]
    for name in ("a.csv", "b.csv"):
        assert _written(_bea(books, *_import(books, name, "--apply"))) == 0


@pytest.mark.parametrize("swap", [False, True], ids=["narration-first", "payee-first"])
def test_one_file_with_a_one_and_a_two_field_row_writes_both(books: Path, swap: bool) -> None:
    rows = [("", "Shop|Branch|Purchase"), ("Shop|Branch", "Purchase")]
    _csv(books, "both.csv", *(reversed(rows) if swap else rows))

    assert _written(_bea(books, *_import(books, "both.csv", "--apply"))) == 2
    assert len(_spent(books)) == 2
    assert _written(_bea(books, *_import(books, "both.csv", "--apply"))) == 0


def test_the_same_pair_twice_is_still_a_duplicate(books: Path) -> None:
    _csv(books, "a.csv", ("Shop|Branch", "Purchase"))
    _csv(books, "again.csv", ("Shop|Branch", "Purchase"))

    assert _written(_bea(books, *_import(books, "a.csv", "--apply"))) == 1
    assert _written(_bea(books, *_import(books, "again.csv", "--apply"))) == 0


def test_rows_without_a_separator_keep_their_ids(books: Path) -> None:
    from bea_engine.importing import _digest_import_id, _hash_base

    _csv(books, "plain.csv", ("Shop", "Purchase"))
    assert _written(_bea(books, *_import(books, "plain.csv", "--apply"))) == 1
    written = (books / "main.bean").read_text()
    (found,) = re.findall(r'import-id: "(csv:sha256:[0-9a-f]+)"', written)

    assert found == _digest_import_id(_hash_base("2024-02-01", "-10 USD", "SHOP|PURCHASE", "Assets:Cash"), 1)


def test_an_older_ambiguous_id_does_not_consume_a_different_pair(books: Path) -> None:
    from bea_engine.importing import _digest_import_id, _hash_base

    _csv(books, "a.csv", ("Shop|Branch", "Purchase"))
    _csv(books, "b.csv", ("Shop", "Branch|Purchase"))
    assert _written(_bea(books, *_import(books, "a.csv", "--apply"))) == 1
    ledger = books / "main.bean"
    text = ledger.read_text()
    (found,) = re.findall(r'import-id: "(csv:sha256:[0-9a-f]+)"', text)
    # What the release before framing wrote for `Shop|Branch` + `Purchase`.
    legacy = _digest_import_id(_hash_base("2024-02-01", "-10 USD", "SHOP|BRANCH|PURCHASE", "Assets:Cash"), 1)
    ledger.write_text(text.replace(found, legacy))

    assert _written(_bea(books, *_import(books, "a.csv", "--apply"))) == 0
    assert _written(_bea(books, *_import(books, "b.csv", "--apply"))) == 1
