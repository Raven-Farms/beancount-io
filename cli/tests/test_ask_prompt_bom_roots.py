"""A leading UTF-8 BOM does not hide the first renamed root from Ask (w5/891).

The root option was matched at the start of a line, and a BOM sits before
the first one, so `option "name_expenses"` written first was skipped.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_ask_prompt_renamed_roots import _system_prompt

RENAMED = 'option "name_expenses" "Aufwand"\noption "operating_currency" "USD"\n'
SENTENCE = "This ledger renames its account roots: Aufwand (for Expenses)."


@pytest.mark.parametrize(
    "prefix",
    [b"\xef\xbb\xbf", b"", b"\xef\xbb\xbf; a comment first\n", b"\xef\xbb\xbf" + b'option "title" "T"\n'],
    ids=["bom-first", "plain", "bom-then-comment", "bom-then-title"],
)
def test_the_renamed_root_reaches_the_model_with_or_without_a_bom(tmp_path: Path, prefix: bytes) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(prefix + RENAMED.encode())
    before = ledger.read_bytes()

    parts = _system_prompt(ledger)

    assert parts[-1].startswith(SENTENCE)
    assert ledger.read_bytes() == before


def test_a_bom_ledger_without_a_rename_adds_nothing(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(b"\xef\xbb\xbf" + b'option "operating_currency" "USD"\n')

    assert all("renames its account roots" not in part for part in _system_prompt(ledger))
