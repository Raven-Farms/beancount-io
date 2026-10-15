"""Editing or losing a plugin module invalidates the load cache (w5/326).

Beancount keys its cache on the ledger files alone, so once a slow ledger was
cached, an edited local plugin went unnoticed: `check` stayed valid and reads
served the old plugin's output until a ledger file changed. A plugin that
could no longer be imported was hidden the same way.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
{option}plugin "{name}"
2020-01-01 open Assets:Checking USD
"""
# The sleep makes the load slow enough for Beancount to write its cache.
NOTE_PLUGIN = """import time
from beancount.core import data
__plugins__ = ["run"]
def run(entries, options_map, config=None):
    time.sleep(1.05)
    meta = data.new_metadata("<plugin>", 0)
    return entries + [data.Note(meta, entries[0].date, "Assets:Checking", "{text}", None, None)], []
"""
REJECTING_PLUGIN = """import collections, time
__plugins__ = ["run"]
E = collections.namedtuple("E", "source message entry")
def run(entries, options_map, config=None):
    time.sleep(1.05)
    return entries, [E(entries[0].meta, "plugin now rejects the books", None)]
"""


def _bea(tmp_path: Path, *args: str, pythonpath: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), *([str(pythonpath)] if pythonpath else [])]),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "books" / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _cached(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "cache" / "bea" / "load-cache").glob("*.picklecache"))


def test_an_edited_local_plugin_is_read_again(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text(LEDGER.format(option='option "insert_pythonpath" "TRUE"\n', name="localplug"))
    plugin = books / "localplug.py"
    plugin.write_text(NOTE_PLUGIN.format(text="VERSION-ONE"))
    first = _bea(tmp_path, "list", "note")
    assert first.returncode == 0, first.stderr
    assert "VERSION-ONE" in first.stdout
    assert _cached(tmp_path)

    time.sleep(0.01)
    plugin.write_text(NOTE_PLUGIN.format(text="VERSION-TWO"))
    assert "VERSION-TWO" in _bea(tmp_path, "list", "note").stdout

    plugin.write_text(REJECTING_PLUGIN)
    check = _bea(tmp_path, "check")
    assert check.returncode == 1
    assert "plugin now rejects the books" in check.stderr + check.stdout
    again = _bea(tmp_path, "check")
    assert again.returncode == 1
    assert "Cache file is corrupted" not in again.stderr


def test_a_plugin_no_longer_importable_is_reported(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text(LEDGER.format(option="", name="pathplug"))
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "pathplug.py").write_text(NOTE_PLUGIN.format(text="ON-PATH"))
    assert _bea(tmp_path, "check", pythonpath=plugins).returncode == 0
    assert _cached(tmp_path)

    lost = _bea(tmp_path, "check")
    assert lost.returncode == 1
    assert "pathplug" in lost.stderr + lost.stdout
