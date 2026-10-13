"""The managed price fetch budget covers response headers too (w5/188).

A feed that sent its status line and then one header every few seconds kept
every socket read short, so the five-second limit never fired until the
server stopped: fifteen seconds for five headers, a minute for twenty, and
then a message that said five. w1/078 bounded the body; this bounds the
whole exchange.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from bea_engine.managed_prices import FetchedFeed, FetchFailed, fetch_managed_price_feed
from tests.test_price import FEED, _run_bea, _write_managed_ledger


class _TrickleHandler(BaseHTTPRequestHandler):
    """`/prices/<ALIAS>` answers at once, or pads its headers when told to."""

    pad_count = 0
    pad_interval = 0.0
    stop = threading.Event()

    def log_message(self, *args: object) -> None:
        pass

    def do_GET(self) -> None:
        body = FEED.encode("utf-8")
        try:
            self.wfile.write(b"HTTP/1.0 200 OK\r\n")
            self.wfile.flush()
            for index in range(type(self).pad_count):
                if type(self).stop.wait(type(self).pad_interval):
                    return
                self.wfile.write(f"X-Pad-{index}: x\r\n".encode("ascii"))
                self.wfile.flush()
            self.wfile.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
        except OSError:
            pass


@pytest.fixture
def trickle_server() -> Iterator[str]:
    _TrickleHandler.pad_count = 0
    _TrickleHandler.pad_interval = 0.0
    _TrickleHandler.stop = threading.Event()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _TrickleHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    _TrickleHandler.stop.set()
    server.shutdown()
    thread.join(timeout=5)


def test_trickled_headers_time_out_within_the_budget(trickle_server: str) -> None:
    # Ten headers 0.4 s apart: every read beats the one-second socket timeout.
    _TrickleHandler.pad_count = 10
    _TrickleHandler.pad_interval = 0.4
    started = time.monotonic()

    result = fetch_managed_price_feed(f"{trickle_server}/prices/BTC-USD", timeout_seconds=1)

    assert time.monotonic() - started < 2.5
    assert isinstance(result, FetchFailed)
    assert result.reason == "timeout"
    assert result.message == "timed out after 1 seconds"


def test_a_prompt_feed_is_fetched_unchanged(trickle_server: str) -> None:
    result = fetch_managed_price_feed(f"{trickle_server}/prices/BTC-USD", timeout_seconds=1)

    assert isinstance(result, FetchedFeed)
    assert result.text == FEED


def test_headers_slower_than_the_budget_still_arrive_when_within_it(trickle_server: str) -> None:
    _TrickleHandler.pad_count = 3
    _TrickleHandler.pad_interval = 0.1

    result = fetch_managed_price_feed(f"{trickle_server}/prices/BTC-USD", timeout_seconds=5)

    assert isinstance(result, FetchedFeed)
    assert result.text == FEED


def test_check_fails_near_five_seconds_on_a_header_trickle(trickle_server: str, tmp_path: Path) -> None:
    # Twelve headers one second apart: twelve seconds without a whole-exchange limit.
    _TrickleHandler.pad_count = 12
    _TrickleHandler.pad_interval = 1.0
    ledger = _write_managed_ledger(tmp_path, trickle_server)
    started = time.monotonic()

    result = _run_bea(tmp_path, trickle_server, "--file", str(ledger), "check")

    elapsed = time.monotonic() - started
    assert result.returncode == 1, result.stdout + result.stderr
    assert "timed out after 5 seconds" in " ".join((result.stdout + result.stderr).split())
    assert elapsed < 9.5, elapsed


def test_check_accepts_the_same_feed_when_it_answers_promptly(trickle_server: str, tmp_path: Path) -> None:
    ledger = _write_managed_ledger(tmp_path, trickle_server)

    result = _run_bea(tmp_path, trickle_server, "--file", str(ledger), "check")

    assert result.returncode == 0, result.stdout + result.stderr
