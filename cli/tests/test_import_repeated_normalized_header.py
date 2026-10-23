"""A repeated page header is matched the way the first header was read (w5/923).

The initial header cells are normalized into the column names, but the repeat
was compared raw, so a header spelled with decomposed accents, an inner format
character, a no-break space or a BOM repeated byte for byte was refused as a
row with a non-date in the date column.
"""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
SPELLINGS = {
    "ascii": lambda: "Description",
    "composed": lambda: unicodedata.normalize("NFC", "Descripción"),
    "decomposed": lambda: unicodedata.normalize("NFD", "Descripción"),
    "format-char": lambda: "Descri​ption",
    "no-break-space": lambda: "Page Description",
    "inner-bom": lambda: "Descri﻿ption",
}


def _write(tmp_path: Path, header: list[str], repeat: list[str] | None) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    with (tmp_path / "bank.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerow(["2024-02-01", "Coffee", "-4.50", "qa-1"])
        if repeat is not None:
            writer.writerow(repeat)
        writer.writerow(["2024-02-02", "Lunch", "-6.25", "qa-2"])


def _mapping(name: str) -> list[str]:
    return [
        "import", "bank.csv", "--account", "Assets:Cash", "--default-account", "Expenses:Food",
        "--csv", f"date=Date,narration={name},amount=Amount,id=Reference",
    ]  # fmt: skip


@pytest.mark.parametrize("style", list(SPELLINGS))
def test_a_repeated_page_header_is_skipped_in_every_spelling(tmp_path: Path, style: str) -> None:
    name = SPELLINGS[style]()
    header = ["Date", name, "Amount", "Reference"]
    _write(tmp_path, header, header)
    normalized = unicodedata.normalize("NFC", "".join(c for c in name if unicodedata.category(c) != "Cf"))
    normalized = "".join(" " if unicodedata.category(c) == "Zs" else c for c in normalized)

    applied = _bea(tmp_path, *_mapping(normalized), "--date-format", "%Y-%m-%d", "--apply")

    assert _written(applied) == 2
    assert _bea(tmp_path, "check").returncode == 0


def test_a_composed_repeat_of_a_decomposed_header_is_skipped_too(tmp_path: Path) -> None:
    decomposed = unicodedata.normalize("NFD", "Descripción")
    composed = unicodedata.normalize("NFC", "Descripción")
    _write(tmp_path, ["Date", decomposed, "Amount", "Reference"], ["Date", composed, "Amount", "Reference"])

    assert _written(_bea(tmp_path, *_mapping(composed), "--apply")) == 2


def test_a_genuine_non_data_row_beginning_with_date_is_still_refused(tmp_path: Path) -> None:
    header = ["Date", "Description", "Amount", "Reference"]
    _write(tmp_path, header, ["Date", "Total", "", ""])
    before = (tmp_path / "main.bean").read_bytes()

    refused = _bea(tmp_path, *_mapping("Description"), "--apply")

    assert refused.returncode == 2, refused.stdout
    assert (tmp_path / "main.bean").read_bytes() == before
