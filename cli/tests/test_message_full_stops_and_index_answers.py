"""One full stop after a price-source error, and a sentence for an unreadable index answer (w5/484).

`balance`/`report` appended `.` to a fetch error that already ended in one,
and `upgrade --check` printed Python's parser text (`Expecting value: line 1
column 1 (char 0)`, `'version'`) for an index that answered something else.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from cli import update
from cli.commands import report
from cli.errors import BeaError


def test_a_source_error_ending_in_a_stop_gets_one(capfd: pytest.CaptureFixture[str]) -> None:
    metadata: dict[str, Any] = {
        "period": {"start": "2026-01-01"},
        "as_of": "2026-10-16",
        "conversion": "at_cost",
        "missing_prices": [],
        "missing_price_summary": None,
        "price_sources": [
            {
                "alias": "BTC-USD",
                "freshness": "recent",
                "observed_at": "2026-10-16T00:00:00Z",
                "revision": "r1",
                "error": "fetch failed (provider): HTTP 503: price service unavailable. Retry later; cached prices "
                "remain usable.",
            }
        ],
    }

    report._heading("Trial Balance", metadata)

    captured = capfd.readouterr()
    printed = captured.out + captured.err
    assert "cached prices remain usable." in printed
    assert ".." not in printed


class _Body(BaseHTTPRequestHandler):
    body = b""

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def index(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_Body]]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Body)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    monkeypatch.setenv("BEA_UPDATE_API_URL", f"http://127.0.0.1:{server.server_address[1]}")
    try:
        yield _Body
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    "body", [b"<!DOCTYPE html><html><body>maintenance</body></html>", b'{"info":{}}', b'{"info":null}', b"[]"]
)
def test_an_unreadable_index_answer_is_one_sentence(index: type[_Body], body: bytes) -> None:
    index.body = body

    with pytest.raises(BeaError) as caught:
        update.check_latest()

    assert str(caught.value).endswith("for a newer release: the index sent an unreadable answer.")


def test_a_readable_answer_still_reads(index: type[_Body]) -> None:
    index.body = b'{"info":{"version":"9.9.9"}}'

    assert update.check_latest() == "9.9.9"


@pytest.mark.parametrize(
    "body", [b'{"info":{"version":null}}', b'{"info":{"version":""}}', b'{"info":{"version":["0.9.0"]}}', b"9"]
)
def test_a_version_that_is_not_a_version_is_unreadable(index: type[_Body], body: bytes) -> None:
    """`str()` read null as "None" (and cached it), and an empty string or a list passed (w5/648)."""
    index.body = body

    with pytest.raises(BeaError) as caught:
        update.check_latest()

    assert str(caught.value).endswith("for a newer release: the index sent an unreadable answer.")
    assert update.read_cache("pypi") is None


def test_a_homebrew_page_without_a_version_is_unreadable(index: type[_Body], monkeypatch: pytest.MonkeyPatch) -> None:
    """An HTML error page from the tap read as "Latest release: unknown" with exit 0 (w5/648)."""
    import os

    monkeypatch.setenv(update.TAP_URL_ENV, os.environ["BEA_UPDATE_API_URL"] + "/bea.rb")
    index.body = b"<html><body>502 Bad Gateway</body></html>"

    with pytest.raises(BeaError) as caught:
        update.check_latest("homebrew")

    assert str(caught.value).endswith("for a newer release: the index sent an unreadable answer.")
    assert update.read_cache("homebrew") is None

    index.body = b'class Bea < Formula\n  version "0.9.1"\nend\n'
    assert update.check_latest("homebrew") == "0.9.1"
