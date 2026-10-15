"""An untraversable `load-cache` directory means an uncached load, not a failure (w5/312).

After w5/220 the cache probes used `Path.is_file`, which re-raises EACCES:
one `sudo bea …` that left `load-cache` root-owned at 0700 failed every read
and write with `PermissionError: [Errno 13]`, exit 1 `validation`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0, reason="POSIX permissions that root ignores"
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening
2026-01-02 * "Open"
  Assets:Checking  5.00 USD
  Equity:Opening
"""


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "xc"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Iterator[Path]:
    (tmp_path / "main.bean").write_text(LEDGER)
    assert _bea(tmp_path, "balance").returncode == 0
    cache = tmp_path / "xc" / "bea" / "load-cache"
    assert cache.is_dir()
    cache.chmod(0o000)
    try:
        yield tmp_path
    finally:
        cache.chmod(0o700)


def test_reads_answer_without_the_cache(books: Path) -> None:
    balance = _bea(books, "balance")
    assert balance.returncode == 0, balance.stderr
    assert "5.00 USD" in balance.stdout
    listed = _bea(books, "--json", "list", "transaction", "--limit", "1")
    assert listed.returncode == 0, listed.stderr
    assert json.loads(listed.stdout)["data"]
    assert "PermissionError" not in balance.stderr + listed.stderr


def test_a_write_lands_without_the_cache(books: Path) -> None:
    result = _bea(books, "add", "note", "--date", "2026-01-05", "-a", "Assets:Checking", "-m", "x")
    assert result.returncode == 0, result.stderr
    assert '2026-01-05 note Assets:Checking "x"' in (books / "main.bean").read_text()
