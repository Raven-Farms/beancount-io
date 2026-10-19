"""A new `--into` file takes the NFC spelling, and a globbed respelling names the file (w5/536).

A file `--into` created took the NFD name pasted from Finder, and the next
keyboard-typed `--into` was refused with wording about an include line that
the glob `Ausgaben/*.bean` never had. (Text keeps the bytes typed, as w5/130
decided; USAGE now says only account names are written NFC.) The NFD spelling
that created the file keeps writing to it on a later run (w5/721).
"""

from __future__ import annotations

import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPENS = """2026-01-01 open Assets:Checking EUR
2026-01-01 open Expenses:Food EUR
"""


def _nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


def _add(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "add", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_a_new_into_file_takes_the_nfc_name_and_takes_later_writes(tmp_path: Path) -> None:
    (tmp_path / "Ausgaben").mkdir()
    (tmp_path / "Ausgaben" / "Jan.bean").write_text(OPENS)
    (tmp_path / "main.bean").write_text('option "operating_currency" "EUR"\ninclude "Ausgaben/*.bean"\n')
    posting = ("-p", "Expenses:Food 1 EUR", "-p", "Assets:Checking")

    first = _add(tmp_path, "transaction", "X", "--date", "2026-02-02", *posting, "--into", _nfd("Ausgaben/März.bean"))
    assert first.returncode == 0, first.stderr
    assert "März.bean" in os.listdir(tmp_path / "Ausgaben")

    second = _add(tmp_path, "transaction", "Y", "--date", "2026-02-03", *posting, "--into", "Ausgaben/März.bean")
    assert second.returncode == 0, second.stderr
    assert (tmp_path / "Ausgaben" / "März.bean").read_text().count('"') >= 4


def test_the_nfd_spelling_that_created_the_file_keeps_writing_to_it(tmp_path: Path) -> None:
    """The second run with the same NFD `--into` writes the NFC file it created (w5/721)."""
    (tmp_path / "Ausgaben").mkdir()
    (tmp_path / "Ausgaben" / "Jan.bean").write_text(OPENS)
    (tmp_path / "main.bean").write_text('option "operating_currency" "EUR"\ninclude "Ausgaben/*.bean"\n')
    posting = ("-p", "Expenses:Food 1 EUR", "-p", "Assets:Checking")

    first = _add(tmp_path, "transaction", "X", "--date", "2026-02-02", *posting, "--into", _nfd("Ausgaben/März.bean"))
    assert first.returncode == 0, first.stderr
    assert "März.bean" in os.listdir(tmp_path / "Ausgaben")

    second = _add(tmp_path, "transaction", "Y", "--date", "2026-02-03", *posting, "--into", _nfd("Ausgaben/März.bean"))
    assert second.returncode == 0, second.stderr
    names = os.listdir(tmp_path / "Ausgaben")
    assert names.count("März.bean") == 1 and len(names) == 2
    assert (tmp_path / "Ausgaben" / "März.bean").read_text().count('"') >= 4


def test_a_globbed_respelling_names_the_file_on_disk(tmp_path: Path) -> None:
    (tmp_path / "Ausgaben").mkdir()
    (tmp_path / "Ausgaben" / _nfd("März.bean")).write_text(OPENS)
    if not (tmp_path / "Ausgaben" / "März.bean").exists():
        pytest.skip("this file system tells NFC and NFD names apart, so there is no respelling to refuse")
    (tmp_path / "main.bean").write_text('option "operating_currency" "EUR"\ninclude "Ausgaben/*.bean"\n')

    result = _add(
        tmp_path, "transaction", "Y", "--date", "2026-02-03", "-p", "Expenses:Food 2 EUR", "-p", "Assets:Checking",
        "--into", "Ausgaben/März.bean",
    )  # fmt: skip

    assert result.returncode == 2, result.stdout + result.stderr
    assert "as the file is named on disk" in result.stderr
    assert "the file's name is NFD" in result.stderr
    assert "include line" not in result.stderr
