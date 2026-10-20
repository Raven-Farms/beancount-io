"""A load cache from an earlier local day is loaded again (w5/782).

Beancount keys its cache on the ledger files alone, and bea's own record
added the plugin fingerprints but no day — so a plugin whose output depends
on today's date (`fava.plugins.amortize_over` books only the parts dated on
or before today) served yesterday's rows until a ledger file changed, with
exit 0. The record now carries the load's local day, and a cache from an
earlier day loads again.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from bea_engine.managed_load import (
    _ENGINE_CACHE_MARK,
    _PLUGIN_RECORD,
    _day_changed,
    _mark_engine_cache,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
option "insert_pythonpath" "TRUE"
plugin "markerplug"
2020-01-01 open Assets:Checking USD
"""
# The sleep makes the load slow enough for Beancount to write its cache; the
# marker stands in for output that legitimately differs between two days.
MARKER_PLUGIN = """import os, time
from beancount.core import data
__plugins__ = ["run"]
def run(entries, options_map, config=None):
    time.sleep(1.05)
    meta = data.new_metadata("<plugin>", 0)
    text = os.environ.get("LEDGER_MARKER", "UNSET")
    return entries + [data.Note(meta, entries[0].date, "Assets:Checking", text, None, None)], []
"""


def _bea(tmp_path: Path, *args: str, marker: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    if marker is not None:
        env["LEDGER_MARKER"] = marker
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "books" / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _cache_file(tmp_path: Path) -> Path:
    caches = sorted((tmp_path / "cache" / "bea" / "load-cache").glob("*.picklecache"))
    assert len(caches) == 1
    return caches[0]


def _record_of(cache: Path) -> dict:
    raw = cache.read_bytes()
    start = raw.rfind(_PLUGIN_RECORD)
    end = raw.rfind(_ENGINE_CACHE_MARK)
    assert start >= 0 and end > start
    return json.loads(raw[start + len(_PLUGIN_RECORD) : end])


def _backdate_record(cache: Path, when: str) -> None:
    """Rewrite the cache's record with an earlier load day, as a new day would find it."""
    raw = cache.read_bytes()
    start = raw.rfind(_PLUGIN_RECORD)
    end = raw.rfind(_ENGINE_CACHE_MARK)
    assert start >= 0 and end > start
    record = json.loads(raw[start + len(_PLUGIN_RECORD) : end])
    record["date"] = when
    cache.write_bytes(raw[:start] + _PLUGIN_RECORD + json.dumps(record).encode("utf-8") + _ENGINE_CACHE_MARK)


def test_a_cache_from_an_earlier_day_is_loaded_again(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text(LEDGER)
    (books / "markerplug.py").write_text(MARKER_PLUGIN)
    first = _bea(tmp_path, "list", "note", marker="DAY-ONE")
    assert first.returncode == 0, first.stderr
    assert "DAY-ONE" in first.stdout
    cache = _cache_file(tmp_path)
    assert _record_of(cache)["date"] == date.today().isoformat()

    # Control: with the day unchanged, the cache is still served.
    assert "DAY-ONE" in _bea(tmp_path, "list", "note", marker="DAY-TWO").stdout

    _backdate_record(cache, (date.today() - timedelta(days=1)).isoformat())
    reread = _bea(tmp_path, "list", "note", marker="DAY-TWO")
    assert reread.returncode == 0, reread.stderr
    assert "DAY-TWO" in reread.stdout
    assert _record_of(cache)["date"] == date.today().isoformat()


def test_the_day_predicate_honours_a_mocked_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import bea_engine.managed_load as managed_load

    cache = tmp_path / "marked.picklecache"
    cache.write_bytes(b"not a real pickle, only the record matters")
    _mark_engine_cache(cache, {"plugin": [], "pythonpath": []})
    assert _day_changed(cache) is False

    real_date = managed_load.date

    class Tomorrow(real_date):  # type: ignore[misc]
        @classmethod
        def today(cls) -> real_date:
            return real_date.today() + timedelta(days=1)

    monkeypatch.setattr(managed_load, "date", Tomorrow)
    assert _day_changed(cache) is True


def test_a_record_without_a_day_loads_again(tmp_path: Path) -> None:
    cache = tmp_path / "legacy.picklecache"
    record = {"names": [], "pythonpath": [], "modules": []}
    cache.write_bytes(b"pickleme" + _PLUGIN_RECORD + json.dumps(record).encode("utf-8") + _ENGINE_CACHE_MARK)
    assert _day_changed(cache) is True
