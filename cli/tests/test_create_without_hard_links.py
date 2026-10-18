"""`bea init` and a write into a new file work where the filesystem has no hard links (w5/605).

A new file was claimed with `os.link(candidate, target)`. FAT and exFAT, the
filesystems of USB sticks and SD cards, refuse that (`ENOTSUP` on macOS,
`EPERM` from Linux's vfat), so every creation failed with a raw `OSError:
[Errno 45]` naming the hidden staging file. `os.link` is made to answer that
way here.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from bea_engine import initiating, protocol
from bea_engine.ledger import write


def _refusing(code: int):  # type: ignore[no-untyped-def]
    def link(source: str | Path, target: str | Path, *args: object, **kwargs: object) -> None:
        raise OSError(code, os.strerror(code), str(source), None, str(target))

    return link


@pytest.fixture(params=[errno.ENOTSUP, errno.EPERM], ids=["ENOTSUP", "EPERM"])
def no_hard_links(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "link", _refusing(request.param))


def _staging_left(directory: Path) -> list[str]:
    return [path.name for path in directory.iterdir() if path.name.startswith(".bea-")]


def test_init_creates_the_ledger(tmp_path: Path, no_hard_links: None) -> None:
    ledger = tmp_path / "books" / "main.bean"

    answer = initiating.answer(ledger, currency="USD", date="2026-01-01")

    assert answer["created"] == str(ledger)
    assert "open Assets:" in ledger.read_text()
    assert _staging_left(ledger.parent) == []


def test_a_write_into_a_new_included_file_creates_it(tmp_path: Path, no_hard_links: None) -> None:
    (tmp_path / "txns").mkdir()
    (tmp_path / "txns" / "2025.bean").write_text("")
    main = tmp_path / "main.bean"
    main.write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\ninclude "txns/*.bean"\n')

    write.append(main, ['2026-02-02 note Assets:Checking "hi"\n'], into=tmp_path / "txns" / "2026.bean")

    assert '2026-02-02 note Assets:Checking "hi"' in (tmp_path / "txns" / "2026.bean").read_text()
    assert _staging_left(tmp_path / "txns") == []


def test_an_existing_name_is_never_replaced(tmp_path: Path, no_hard_links: None) -> None:
    candidate, target = tmp_path / ".bea-candidate.tmp", tmp_path / "main.bean"
    candidate.write_text("new\n")
    target.write_text("theirs\n")

    with pytest.raises(FileExistsError):
        write.claim_new_file(candidate, target)

    assert target.read_text() == "theirs\n"


def test_any_other_refusal_is_said_in_beas_words(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "link", _refusing(errno.ENOSPC))
    candidate, target = tmp_path / ".bea-candidate.tmp", tmp_path / "main.bean"
    candidate.write_text("new\n")

    with pytest.raises(protocol.LedgerError) as raised:
        write.claim_new_file(candidate, target)

    assert str(raised.value) == f"Cannot create {target} (No space left on device); nothing was written."
    assert not target.exists()
