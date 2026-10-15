"""An include whose file name holds a newline does not break writes (w5/301).

Every root-staged write failed with "Cannot locate an include path in the
ledger.": the staged copy respelled `include "a\\nb.bean"` with a raw newline,
and the lexer reports a string spanning lines at its last line, where the
search for it started. `price export` wrote a root `check` then refused.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Equity:Opening USD\n'

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="newline in a file name")


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books.parent / "config"),
        XDG_CACHE_HOME=str(books.parent / "cache"),
        XDG_DATA_HOME=str(books.parent / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("spelling", ["a\\nb.bean", "a\nb.bean"], ids=["escaped", "raw"])
def test_a_root_write_and_an_export_keep_the_include(tmp_path: Path, spelling: str) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (books / "a\nb.bean").write_text('2026-01-03 note Assets:Checking "inc"\n')
    ledger = books / "main.bean"
    ledger.write_text(HEADER + f'include "{spelling}"\n')

    added = _bea(books, "-f", str(ledger), "add", "note", "--date", "2026-01-05", "-a", "Assets:Checking", "-m", "root")
    assert added.returncode == 0, added.stderr
    assert '"root"' in ledger.read_text()

    exported = _bea(books, "-f", str(ledger), "price", "export", "-o", "exp")
    assert exported.returncode == 0, exported.stderr
    assert 'include "a\\nb.bean"' in (books / "exp" / "main.bean").read_text()
    listed = _bea(books, "-f", str(books / "exp" / "main.bean"), "list", "note")
    assert listed.returncode == 0, listed.stderr
    assert "inc" in listed.stdout and "root" in listed.stdout
