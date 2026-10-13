"""A price feed that answers with something other than HTTP degrades to the cache."""

from __future__ import annotations

import json
import socket
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from bea_engine.managed_prices import FetchFailed, fetch_managed_price_feed
from tests.test_price import FEED, _run_bea, _write_managed_ledger

GOOD = b'HTTP/1.0 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nETag: "r1"\r\nContent-Length: %d\r\n\r\n%s' % (
    len(FEED.encode()),
    FEED.encode(),
)
JUNK = {
    "not-http": b"SSH-2.0-OpenSSH_9.0\r\n",
    "no-status-line": b"\r\n\r\n",
    "over-long-header": b"HTTP/1.0 200 OK\r\nX-Pad: " + b"a" * 70000 + b"\r\n\r\n",
    "too-many-headers": b"HTTP/1.0 200 OK\r\n" + b"".join(b"X-%d: 1\r\n" % n for n in range(150)) + b"\r\n",
    "over-long-chunk-size": b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n" + b"0" * 70000 + b"\r\n",
}


class _RawFeed:
    """A loopback listener that answers every request with `reply`, verbatim."""

    def __init__(self) -> None:
        self.reply = GOOD
        self.hits = 0
        self._listener = socket.create_server(("127.0.0.1", 0))
        self.url = f"http://127.0.0.1:{self._listener.getsockname()[1]}"
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while True:
            try:
                connection, _ = self._listener.accept()
            except OSError:
                return
            with connection:
                connection.settimeout(5)
                try:
                    request = b""
                    while b"\r\n\r\n" not in request:
                        chunk = connection.recv(4096)
                        if not chunk:
                            break
                        request += chunk
                    self.hits += 1
                    connection.sendall(self.reply)
                    connection.shutdown(socket.SHUT_WR)
                    # Drain until the client hangs up, so the close is never a reset.
                    while connection.recv(4096):
                        pass
                except OSError:
                    pass

    def close(self) -> None:
        self._listener.close()
        self._thread.join(timeout=5)


@pytest.fixture
def raw_feed() -> Iterator[_RawFeed]:
    feed = _RawFeed()
    yield feed
    feed.close()


def _assert_no_python_exception(text: str) -> None:
    for name in ("BadStatusLine", "LineTooLong", "HTTPException", "Traceback", "--debug"):
        assert name not in text


@pytest.mark.parametrize("junk", JUNK.values(), ids=JUNK.keys())
def test_fetch_reports_a_malformed_reply_as_a_network_failure(raw_feed: _RawFeed, junk: bytes) -> None:
    raw_feed.reply = junk

    result = fetch_managed_price_feed(f"{raw_feed.url}/prices/BTC-USD", timeout_seconds=5)

    assert isinstance(result, FetchFailed)
    assert result.reason == "network"
    assert "malformed HTTP response" in result.message


@pytest.mark.parametrize("junk", JUNK.values(), ids=JUNK.keys())
def test_commands_serve_the_cached_revision_through_a_malformed_reply(
    raw_feed: _RawFeed, tmp_path: Path, junk: bytes
) -> None:
    ledger = _write_managed_ledger(tmp_path, raw_feed.url)
    assert _run_bea(tmp_path, raw_feed.url, "--file", str(ledger), "check").returncode == 0
    raw_feed.reply = junk

    refresh = _run_bea(tmp_path, raw_feed.url, "--file", str(ledger), "price", "refresh")

    assert refresh.returncode == 1
    assert (
        "BTC-USD: fetch failed (network): the price service sent a malformed HTTP response; serving revision r1"
        in refresh.stderr
    )
    _assert_no_python_exception(refresh.stdout + refresh.stderr)

    # The failure is recorded, so the commands after it serve the cache
    # without asking the broken feed again.
    hits = raw_feed.hits
    check = _run_bea(tmp_path, raw_feed.url, "--file", str(ledger), "check")
    assert check.returncode == 0, check.stderr
    _assert_no_python_exception(check.stdout + check.stderr)
    write = _run_bea(
        tmp_path,
        raw_feed.url,
        "--file",
        str(ledger),
        "add",
        "note",
        "-a",
        "Assets:Broker",
        "--date",
        "2024-02-01",
        "-m",
        "n",
        "--allow-errors",
    )
    assert write.returncode == 0, write.stderr
    _assert_no_python_exception(write.stdout + write.stderr)
    assert '2024-02-01 note Assets:Broker "n"' in ledger.read_text()
    prices = _run_bea(tmp_path, raw_feed.url, "--file", str(ledger), "list", "price")
    assert "113500.50 USD" in prices.stdout
    assert raw_feed.hits == hits


def test_json_refresh_names_the_source_and_the_served_revision(raw_feed: _RawFeed, tmp_path: Path) -> None:
    ledger = _write_managed_ledger(tmp_path, raw_feed.url)
    assert _run_bea(tmp_path, raw_feed.url, "--file", str(ledger), "check").returncode == 0
    raw_feed.reply = JUNK["not-http"]

    result = _run_bea(tmp_path, raw_feed.url, "--json", "--file", str(ledger), "price", "refresh")

    assert result.returncode == 1
    assert not result.stdout
    (source,) = json.loads(result.stderr)["error"]["result"]["sources"]
    assert source["url"] == f"{raw_feed.url}/prices/BTC-USD"
    assert source["revision"] == "r1"
    assert "malformed HTTP response" in source["error"]
    _assert_no_python_exception(result.stderr)


def test_uncached_malformed_reply_keeps_the_books_loadable(raw_feed: _RawFeed, tmp_path: Path) -> None:
    ledger = _write_managed_ledger(tmp_path, raw_feed.url)
    raw_feed.reply = JUNK["not-http"]

    result = _run_bea(tmp_path, raw_feed.url, "--file", str(ledger), "check")

    assert result.returncode == 1
    _assert_no_python_exception(result.stdout + result.stderr)
    assert "managed price source unavailable" in result.stderr
    assert "malformed HTTP response" in result.stderr


def test_well_formed_server_error_still_degrades_as_a_provider_failure(raw_feed: _RawFeed, tmp_path: Path) -> None:
    ledger = _write_managed_ledger(tmp_path, raw_feed.url)
    assert _run_bea(tmp_path, raw_feed.url, "--file", str(ledger), "check").returncode == 0
    raw_feed.reply = b"HTTP/1.0 500 Internal Server Error\r\nContent-Length: 0\r\n\r\n"

    refresh = _run_bea(tmp_path, raw_feed.url, "--file", str(ledger), "price", "refresh")

    assert refresh.returncode == 1
    assert "fetch failed (provider): HTTP 500" in refresh.stderr
    assert "serving revision r1" in refresh.stderr
    assert _run_bea(tmp_path, raw_feed.url, "--file", str(ledger), "check").returncode == 0
