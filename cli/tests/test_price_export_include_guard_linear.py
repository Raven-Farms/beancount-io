"""The `price export` include guard costs one lookup per file, not one per file and pattern (w5/317).

The guard resolved every planned path once per include pattern, so a ledger
of 1,500 literal includes took 37 s to export while `check` took under one.
Literal includes are now resolved once into a lookup; only wildcard patterns
are matched against each file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bea_engine import managed_load
from bea_engine.ledger import write
from bea_engine.protocol import UsageError

HEADER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n'


def _books(tmp_path: Path, count: int, extra: str = "") -> Path:
    books = tmp_path / "books"
    books.mkdir()
    for index in range(count):
        (books / f"f{index}.bean").write_text(f'2026-01-02 note Assets:Checking "n{index}"\n')
    includes = "".join(f'include "f{index}.bean"\n' for index in range(count))
    (books / "main.bean").write_text(HEADER + includes + extra)
    return books / "main.bean"


def test_wildcard_matching_grows_linearly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = _books(tmp_path, 200, 'include "*/*.bean"\n')
    calls: list[tuple[Path, str]] = []
    original = write._included_new_file

    def counted(target: Path, pattern: str, **options: bool) -> bool:
        calls.append((target, pattern))
        return original(target, pattern, **options)

    monkeypatch.setattr(write, "_included_new_file", counted)
    exported = managed_load.export_portable(ledger, tmp_path / "outside", offline=True, root=tmp_path / "cache")

    assert len(exported.files) == 201
    # One wildcard pattern, matched once against each of the 201 planned files
    # and the one directory the export creates (w5/814).
    assert len(calls) <= 202
    assert {pattern for _, pattern in calls} == {str(ledger.parent / "*/*.bean")}


def test_a_literal_include_still_claims_its_new_file(tmp_path: Path) -> None:
    ledger = _books(tmp_path, 3, 'include "snap/main.bean"\n')
    with pytest.raises(UsageError, match="its include pattern .*snap/main.bean matches that path"):
        managed_load.export_portable(ledger, ledger.parent / "snap", offline=True, root=tmp_path / "cache")
    assert not (ledger.parent / "snap").exists()


def test_a_wildcard_include_still_claims_a_new_directory(tmp_path: Path) -> None:
    ledger = _books(tmp_path, 3, 'include "*/*.bean"\n')
    with pytest.raises(UsageError, match="would become part of the ledger being exported"):
        managed_load.export_portable(ledger, ledger.parent / "snap", offline=True, root=tmp_path / "cache")
