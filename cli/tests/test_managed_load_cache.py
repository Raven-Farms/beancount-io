"""A ledger with a managed price include is answered from a load cache (w5/576).

The managed load staged the root under a fresh random name every time, so
Beancount's own cache, keyed on that name, never answered: every read
re-parsed the whole ledger (3.8 s each at 60k transactions, against 1.1 s
cached without the include). The load keeps its own cache, invalidated by the
ledger's files and the feed revisions in use.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest
from beancount import loader

from bea_engine.managed_load import load_with_sources
from tests.test_price import FEED, _FeedHandler, _managed_ledger
from tests.test_price import feed_server as feed_server

TXNS = '2024-02-01 * "Lunch"\n  Expenses:Food  5 USD\n  Assets:Broker  -5 USD\n'


@pytest.fixture
def parses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    """Each full parse of the staged ledger, with every load slow enough to cache."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))
    monkeypatch.setattr(loader, "PICKLE_CACHE_THRESHOLD", 0)
    seen: list[str] = []
    real = loader.load_file

    def counting(filename: Any, *args: Any, **kwargs: Any) -> Any:
        seen.append(str(filename))
        return real(filename, *args, **kwargs)

    monkeypatch.setattr(loader, "load_file", counting)
    return seen


def _read(ledger: Path, feed_server: str, **kwargs: Any) -> Any:
    origins = (f"http://127.0.0.1:{feed_server.rsplit(':', 1)[1]}",)
    return load_with_sources(ledger, origins=origins, root=ledger.parent / "price-cache", **kwargs)


def _narrations(loaded: Any) -> list[str]:
    return [entry.narration for entry in loaded.entries if hasattr(entry, "narration")]


def test_a_second_read_is_served_from_the_cache(feed_server: str, tmp_path: Path, parses: list[str]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(_managed_ledger(feed_server) + TXNS)

    first = _read(ledger, feed_server)
    second = _read(ledger, feed_server, offline=True)

    assert len(parses) == 1, parses
    assert _narrations(second) == _narrations(first) == ["Lunch"]
    assert [error.message for error in second.errors] == [error.message for error in first.errors]
    assert second.sources[0].revision == first.sources[0].revision


def test_an_edited_file_is_parsed_again(feed_server: str, tmp_path: Path, parses: list[str]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(_managed_ledger(feed_server) + TXNS)
    _read(ledger, feed_server)

    time.sleep(0.01)
    ledger.write_text(_managed_ledger(feed_server) + TXNS + TXNS.replace("Lunch", "Dinner"))
    edited = _read(ledger, feed_server, offline=True)

    assert len(parses) == 2, parses
    assert _narrations(edited) == ["Lunch", "Dinner"]


def test_a_refreshed_feed_is_parsed_again(feed_server: str, tmp_path: Path, parses: list[str]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(_managed_ledger(feed_server) + TXNS)
    _read(ledger, feed_server)
    newer = FEED.replace("; revision: r1", "; revision: r2") + "2026-09-12 price BTC 115000.00 USD\n"
    _FeedHandler.routes["/prices/BTC-USD"] = {
        "body": newer.encode("utf-8"),
        "headers": {"Content-Type": "text/plain; charset=utf-8", "ETag": '"r2"'},
        "etag": '"r2"',
        "etag_match": True,
    }

    refreshed = _read(ledger, feed_server, now=time.time() + 10 * 86400)

    assert len(parses) == 2, parses
    assert "115000.00" in {
        str(entry.amount.number) for entry in refreshed.entries if hasattr(entry, "amount") and entry.amount
    }


def test_disable_variable_forces_a_fresh_managed_load_and_removes_the_cache(
    feed_server: str, tmp_path: Path, parses: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`BEANCOUNT_DISABLE_LOAD_CACHE` bypasses the `.managed` cache like upstream's (w5/776)."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(_managed_ledger(feed_server) + TXNS)
    _read(ledger, feed_server)
    assert len(parses) == 1
    assert list((tmp_path / "xdg-cache").rglob("*.managed"))

    before = ledger.stat()
    ledger.write_text(_managed_ledger(feed_server) + TXNS.replace("Expenses:Food", "Expenses:Fodo"))
    os.utime(ledger, ns=(before.st_atime_ns, before.st_mtime_ns))
    stale = _read(ledger, feed_server, offline=True)

    assert len(parses) == 1, parses
    assert [error.message for error in stale.errors] == []

    monkeypatch.setenv("BEANCOUNT_DISABLE_LOAD_CACHE", "1")
    fresh = _read(ledger, feed_server, offline=True)

    assert len(parses) == 2, parses
    assert any("Expenses:Fodo" in error.message for error in fresh.errors)
    assert list((tmp_path / "xdg-cache").rglob("*.managed")) == []
