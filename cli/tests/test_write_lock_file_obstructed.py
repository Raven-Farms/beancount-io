"""A lock file that is not a regular file is named, not misreported (w5/593).

A FIFO at `$XDG_CACHE_HOME/bea/locks/<key>.lock` opened, then failed as
`UnsupportedOperation: File or stream is not seekable` (exit 1), naming no
path. A directory there was blamed on the lock directory, which was fine.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2024-01-01 open Assets:Cash USD\n"

pytestmark = pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX file types")


def _add_price(tmp_path: Path, amount: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    command = ["--json", "-f", str(tmp_path / "main.bean"), "add", "price", "--commodity", "AAPL"]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *command, "--amount", amount, "--date", "2024-01-05"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
        check=False,
    )


@pytest.mark.parametrize(("kind", "what"), [("fifo", "a named pipe"), ("directory", "a directory")])
def test_a_lock_path_something_else_occupies_is_named(tmp_path: Path, kind: str, what: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    first = _add_price(tmp_path, "100 USD")
    assert first.returncode == 0, first.stderr
    (lock,) = (tmp_path / "cache" / "bea" / "locks").glob("*.lock")
    before = ledger.read_text()
    lock.unlink()
    if kind == "fifo":
        os.mkfifo(lock)
    else:
        lock.mkdir()

    result = _add_price(tmp_path, "101 USD")

    assert result.returncode == 3, result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "auth"
    assert f"Cannot take the write lock: {lock} is {what}, not a lock file." in error["message"]
    assert "Nothing was written" in error["message"]
    assert "lock directory" not in error["message"]
    assert "UnsupportedOperation" not in error["message"]
    assert ledger.read_text() == before
