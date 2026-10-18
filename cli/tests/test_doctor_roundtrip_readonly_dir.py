"""`doctor roundtrip` beside a ledger in a read-only folder is a one-line permission failure (w5/572).

Roundtrip writes scratch copies beside the ledger. Upstream raised a
PermissionError, then crashed again in its own cleanup: 34 lines of double
traceback, exit 1, where the exit table gives a permission failure 3.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root writes to read-only folders")
def test_an_unwritable_folder_exits_3_in_one_line(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    ledger = books / "main.bean"
    ledger.write_text("2024-01-01 open Assets:Cash USD\n")
    books.chmod(0o555)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    try:
        result = subprocess.run(
            [sys.executable, "-m", "cli.main", "doctor", "roundtrip", str(ledger)],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )
    finally:
        books.chmod(0o755)

    assert result.returncode == 3, result.stdout + result.stderr
    assert result.stderr.splitlines() == [
        f"Error: doctor roundtrip writes scratch copies beside the ledger, and {books} is not writable. "
        "Nothing was written."
    ]
    assert sorted(path.name for path in books.iterdir()) == ["main.bean"]
