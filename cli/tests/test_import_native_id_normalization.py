"""A decomposed native bank ID matches the composed one the ledger holds (w5/919).

The loader reads ledger text as NFC and an incoming row kept its typed form,
so an unchanged NFD reference became a possible duplicate and the same
reference with a changed amount was written as new, beside the first.
"""

from __future__ import annotations

import csv
import json
import unicodedata
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
REFERENCE = "référence-1"
RUN = [
    "import", "bank.csv", "--account", "Assets:Cash", "--default-account", "Expenses:Food",
    "--csv", "date=Date,narration=Description,amount=Amount,id=ID",
]  # fmt: skip


def _csv(tmp_path: Path, amount: str, form: str) -> None:
    with (tmp_path / "bank.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Date", "Description", "Amount", "ID"])
        writer.writerow(["2024-02-01", "Coffee", amount, unicodedata.normalize(form, REFERENCE)])


def _cash(tmp_path: Path) -> Decimal:
    result = _bea(tmp_path, "query", "SELECT sum(number) WHERE account = 'Assets:Cash'")
    return Decimal(str(json.loads(result.stdout)["data"]["rows"][0][0]))


@pytest.mark.parametrize(
    ("first", "second"), [("NFD", "NFD"), ("NFC", "NFD"), ("NFD", "NFC")], ids=["nfd-nfd", "nfc-nfd", "nfd-nfc"]
)
@pytest.mark.parametrize("policy", ["skip", "include"])
def test_an_unchanged_reference_is_an_exact_duplicate(tmp_path: Path, first: str, second: str, policy: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    _csv(tmp_path, "-4.50", first)
    assert _written(_bea(tmp_path, *RUN, "--apply")) == 1

    _csv(tmp_path, "-4.50", second)
    again = _bea(tmp_path, *RUN, "--duplicates", policy, "--apply")

    assert _written(again) == 0
    assert _cash(tmp_path) == Decimal("-4.50")


@pytest.mark.parametrize(
    ("first", "second"), [("NFD", "NFD"), ("NFC", "NFD"), ("NFD", "NFC")], ids=["nfd-nfd", "nfc-nfd", "nfd-nfc"]
)
def test_the_same_reference_with_a_changed_amount_is_a_conflict(tmp_path: Path, first: str, second: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    _csv(tmp_path, "-4.50", first)
    assert _written(_bea(tmp_path, *RUN, "--apply")) == 1
    before = (tmp_path / "main.bean").read_bytes()

    _csv(tmp_path, "-6.25", second)
    changed = _bea(tmp_path, *RUN, "--apply")

    assert changed.returncode == 4, changed.stdout
    assert (tmp_path / "main.bean").read_bytes() == before
    assert _cash(tmp_path) == Decimal("-4.50")


def test_references_that_differ_only_in_case_stay_distinct(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    _csv(tmp_path, "-4.50", "NFD")
    assert _written(_bea(tmp_path, *RUN, "--apply")) == 1

    with (tmp_path / "bank.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Date", "Description", "Amount", "ID"])
        writer.writerow(["2024-02-01", "Coffee", "-4.50", unicodedata.normalize("NFD", REFERENCE.upper())])

    assert _written(_bea(tmp_path, *RUN, "--duplicates", "include", "--apply")) == 1
