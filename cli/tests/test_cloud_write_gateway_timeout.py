"""A gateway timeout on a cloud write is an unknown outcome, exit 4 (w5/517).

504 and Cloudflare's 520–524 mean the origin received the request and did
not finish answering, the same unknown outcome as bea's own timeout, but
they exited 1 with "Server error" and invited a retry that hit 409 or 404.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = b"<html><body><h1>504 Gateway Time-out</h1></body></html>"


class _Gateway(BaseHTTPRequestHandler):
    status = 504

    def _answer(self) -> None:
        self.send_response(type(self).status)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    do_GET = do_POST = do_DELETE = _answer  # noqa: N815 - BaseHTTPRequestHandler's spelling

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def gateway() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Gateway)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _bea(tmp_path: Path, url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_API_URL=url,
        BEA_TOKEN="test-token",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-y", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize("status", [504, 524])
@pytest.mark.parametrize(
    ("args", "operation"),
    [
        (("cloud", "ledger", "create", "newbook"), "Creating ledger 'newbook'"),
        (("cloud", "ledger", "delete", "qa/books"), "Deleting ledger 'qa/books'"),
    ],
    ids=["create", "delete"],
)
def test_a_gateway_timeout_on_a_write_is_unknown(
    tmp_path: Path, gateway: str, status: int, args: tuple[str, ...], operation: str
) -> None:
    _Gateway.status = status

    result = _bea(tmp_path, gateway, *args)

    assert result.returncode == 4, result.stdout + result.stderr
    error = json.loads(result.stdout or result.stderr)["error"]
    assert error["category"] == "conflict"
    assert error["message"].startswith(f"{operation} timed out at the server's gateway (HTTP {status})")
    assert "check the current state before retrying" in error["message"]


def test_a_plain_server_error_on_a_write_stays_exit_1(tmp_path: Path, gateway: str) -> None:
    _Gateway.status = 500

    result = _bea(tmp_path, gateway, "cloud", "ledger", "create", "newbook")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Server error (HTTP 500)." in result.stdout + result.stderr


def test_a_gateway_timeout_on_a_read_stays_a_server_error(tmp_path: Path, gateway: str) -> None:
    _Gateway.status = 504

    result = _bea(tmp_path, gateway, "cloud", "ledger", "list")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Server error (HTTP 504)." in result.stdout + result.stderr
