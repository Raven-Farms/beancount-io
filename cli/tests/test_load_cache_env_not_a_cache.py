"""A `BEANCOUNT_LOAD_CACHE_FILENAME` naming a file that is no load cache is refused (w5/418).

Beancount removes a cache it cannot unpickle, and bea dropped any cache it
had not written, so every read deleted the named note or CSV with exit 0; a
FIFO hung the load and a device was opened as a cache.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


def _bea(books: Path, cache: str, *args: str, plugins: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), *([str(plugins)] if plugins else [])]),
        TERM="dumb",
        NO_COLOR="1",
        BEANCOUNT_LOAD_CACHE_FILENAME=cache,
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    "command",
    [
        ["balance"],
        ["list", "transaction"],
        ["query", "SELECT 1"],
        ["add", "note", "--date", "2026-01-02", "-a", "Assets:Cash", "-m", "x"],
        ["check"],
    ],
    ids=["balance", "list", "query", "add", "check"],
)
def test_a_user_file_is_refused_and_kept(tmp_path: Path, command: list[str]) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    notes = tmp_path / "notes.txt"
    notes.write_text("my notes\n")

    result = _bea(tmp_path, str(notes), *command)

    assert result.returncode == 2, result.stderr
    assert f"names {notes}, which is not a Beancount load cache" in result.stderr
    assert "Nothing was changed." in result.stderr
    assert notes.read_text() == "my notes\n"
    assert (tmp_path / "main.bean").read_text() == LEDGER


@pytest.mark.skipif(sys.platform == "win32", reason="FIFOs and /dev/null")
@pytest.mark.parametrize("target", ["fifo", "/dev/null"])
def test_a_special_file_is_refused_without_reading_it(tmp_path: Path, target: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    path = tmp_path / "p.fifo"
    if target == "fifo":
        os.mkfifo(path)
    result = _bea(tmp_path, str(path) if target == "fifo" else target, "balance")
    assert result.returncode == 2, result.stderr
    assert "which is not a regular file" in result.stderr


def test_a_real_cache_at_the_path_still_works(tmp_path: Path) -> None:
    """A load over Beancount's one-second threshold writes the cache the next read uses."""
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "slow_plugin.py").write_text(
        textwrap.dedent(
            """
            import time
            __plugins__ = ["slow"]
            def slow(entries, options):
                time.sleep(1.2)
                return entries, []
            """
        )
    )
    (tmp_path / "main.bean").write_text('plugin "slow_plugin"\n' + LEDGER)
    cache = tmp_path / "ledger.picklecache"

    first = _bea(tmp_path, str(cache), "balance", plugins=plugins)
    assert first.returncode == 0, first.stderr
    assert cache.is_file()

    second = _bea(tmp_path, str(cache), "balance", plugins=plugins)
    assert second.returncode == 0, second.stderr
    assert cache.is_file()
