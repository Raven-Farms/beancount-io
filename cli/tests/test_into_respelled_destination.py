"""`--into` in another letter case or Unicode form names the spelling bea takes (w5/434).

The refusal said "the name as it is on disk (X.bean)" while showing the
include line's base name, which is all bea accepts, even when the user had
passed the on-disk name; and a new file under a glob include, its folder in
another case, was called "not included".
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POSTING = ["-p", "Expenses:Food 1 USD", "-p", "Assets:Cash"]


def _case_insensitive(directory: Path) -> bool:
    probe = directory / "CaseProbe"
    probe.write_text("")
    try:
        return (directory / "caseprobe").exists()
    finally:
        probe.unlink()


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "add", "transaction", "T", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    if not _case_insensitive(tmp_path):
        pytest.skip("needs a case-insensitive volume")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "x.bean").write_text("")
    (tmp_path / "months").mkdir()
    (tmp_path / "months" / "jan.bean").write_text("")
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\ninclude "Sub/X.bean"\ninclude "months/*.bean"\n'
        "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n"
    )
    return tmp_path


def test_an_existing_file_names_the_include_lines_spelling(books: Path) -> None:
    refused = _bea(books, "--date", "2026-01-05", *POSTING, "--into", "sub/x.bean")
    assert refused.returncode == 2, refused.stderr
    assert "Pass --into Sub/X.bean as the include line spells it. Nothing was written." in refused.stderr
    assert "as it is on disk" not in refused.stderr

    accepted = _bea(books, "--date", "2026-01-05", *POSTING, "--into", "Sub/X.bean")
    assert accepted.returncode == 0, accepted.stderr


def test_a_new_glob_file_in_another_case_names_the_directory_the_glob_lists(books: Path) -> None:
    refused = _bea(books, "--date", "2026-02-05", *POSTING, "--into", "MONTHS/feb.bean")
    assert refused.returncode == 2, refused.stderr
    assert f"is in the directory {books / 'months'} spelled in another letter case" in refused.stderr
    assert "Pass --into months/feb.bean as the include line spells it." in refused.stderr
    assert "not included" not in refused.stderr
    assert not (books / "months" / "feb.bean").exists()


def test_a_unicode_form_difference_is_named(books: Path) -> None:
    nfc, nfd = unicodedata.normalize("NFC", "réel.bean"), unicodedata.normalize("NFD", "réel.bean")
    (books / "sub" / nfd).write_text("")
    if not (books / "sub" / nfc).exists():
        pytest.skip("needs a normalization-insensitive volume")
    main = books / "main.bean"
    main.write_text(main.read_text() + f'include "sub/{nfc}"\n')

    refused = _bea(books, "--date", "2026-01-05", *POSTING, "--into", f"sub/{nfd}")

    assert refused.returncode == 2, refused.stderr
    assert f"Pass --into {shlex.quote(f'sub/{nfc}')} as the include line spells it." in refused.stderr
    assert "The two differ only in Unicode form; the include line is NFC." in refused.stderr
