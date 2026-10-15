"""A `../` include reached through a symlinked directory is the file the loader opens (w5/451).

Beancount `normpath`s every include match, so `link/../other.bean` beside
`main.bean` is `./other.bean` even when `link` points at `real/sub`. bea's
walker resolved it physically to `real/other.bean`: `format -o other.bean`
overwrote the loaded include, `format -i` formatted a file nothing loads,
and `--into real/other.bean` looped on "ledger changed; retry".
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL = '2026-01-03 * "PHYSICAL real/other"\n  Assets:Cash 1 USD\n  Equity:O\n'
LEXICAL = '2026-01-04 * "LEXICAL root/other"\n  Assets:Cash 5 USD\n  Equity:O\n'

pytestmark = pytest.mark.skipif(os.name != "posix", reason="symlinked directory")


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "real" / "sub").mkdir(parents=True)
    (tmp_path / "link").symlink_to("real/sub")
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\ninclude "link/f.bean"\n'
        "2026-01-01 open Assets:Cash USD\n2026-01-01 open Equity:O USD\n"
    )
    (tmp_path / "real" / "sub" / "f.bean").write_text('include "../other.bean"\n')
    (tmp_path / "real" / "other.bean").write_text(PHYSICAL)
    (tmp_path / "other.bean").write_text(LEXICAL)
    return tmp_path


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
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_format_output_refuses_the_loaded_include(books: Path) -> None:
    result = _bea(books, "format", str(books / "main.bean"), "-o", str(books / "other.bean"))
    assert result.returncode == 2, result.stderr
    assert "would overwrite the ledger it reads" in result.stderr
    assert (books / "other.bean").read_text() == LEXICAL


def test_format_in_place_formats_the_loaded_include(books: Path) -> None:
    (books / "other.bean").write_text(LEXICAL.replace("Assets:Cash 5", "Assets:Cash      5"))
    result = _bea(books, "format", "-i", str(books / "main.bean"))
    assert result.returncode == 0, result.stderr
    assert f"formatted: {books / 'other.bean'}" in result.stderr + result.stdout
    assert (books / "real" / "other.bean").read_text() == PHYSICAL


def test_into_the_physical_twin_is_refused_once_not_looped(books: Path) -> None:
    result = _bea(
        books,
        "-f",
        str(books / "main.bean"),
        "add",
        "note",
        "--date",
        "2026-01-05",
        "-a",
        "Assets:Cash",
        "-m",
        "x",
        "--into",
        "real/other.bean",
    )
    assert result.returncode == 2, result.stderr
    assert "is not included by" in result.stderr
    assert "changed" not in result.stderr
