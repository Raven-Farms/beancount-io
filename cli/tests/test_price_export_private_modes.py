"""`price export` copies are no more readable than their sources (w5/316).

The export wrote with the umask: a `0600` ledger, its include and its receipt
came out `0644` under `0755` directories, beside the private originals.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening
include "private.bean"
2026-01-03 document Assets:Checking "receipts/r.pdf"
"""


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _export(books: Path) -> Path:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books.parent / "config"),
        XDG_CACHE_HOME=str(books.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "price", "export"],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        preexec_fn=lambda: os.umask(0o022),  # noqa: PLW1509 - no threads started yet
    )
    assert result.returncode == 0, result.stderr
    return books / "main-export"


@pytest.mark.parametrize(("file_mode", "dir_mode"), [(0o600, 0o700), (0o644, 0o755)], ids=["private", "shared"])
def test_copies_keep_their_sources_modes(tmp_path: Path, file_mode: int, dir_mode: int) -> None:
    books = tmp_path / "books"
    (books / "receipts").mkdir(parents=True)
    (books / "main.bean").write_text(MAIN)
    (books / "private.bean").write_text('2026-01-02 * "x"\n  Assets:Checking  1 USD\n  Equity:Opening\n')
    (books / "receipts" / "r.pdf").write_bytes(b"pdf")
    for name in ("main.bean", "private.bean", "receipts/r.pdf"):
        (books / name).chmod(file_mode)
    (books / "receipts").chmod(dir_mode)

    export = _export(books)

    for name in ("main.bean", "private.bean", "receipts/r.pdf"):
        assert _mode(export / name) == file_mode, name
    assert _mode(export / "receipts") == 0o700
    assert (export / "receipts" / "r.pdf").read_bytes() == b"pdf"
