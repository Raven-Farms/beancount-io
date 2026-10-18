"""Cloud gateway connection failures differ from ambiguous write outcomes (w5/690)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = b"2026-01-01 open Assets:Cash USD\n"
COMMANDS = {
    "create": ["cloud", "ledger", "create", "newbook"],
    "delete": ["cloud", "ledger", "delete", "qa/books"],
    "logout": ["cloud", "logout"],
    "read": ["cloud", "ledger", "list"],
}
REQUESTS = {
    "create": ("POST", "/api-gateway/v1/ledgers"),
    "delete": ("DELETE", "/api-gateway/v1/ledgers/qa/books"),
    "logout": ("POST", "/api-gateway/v1/logout"),
    "read": ("GET", "/api-gateway/v1/ledgers"),
}


@dataclass
class Gateway:
    url: str = ""
    status: int = 521
    seen: list[tuple[str, str, bytes]] = field(default_factory=list)


@pytest.fixture
def gateway() -> Iterator[Gateway]:
    state = Gateway()

    class Handler(BaseHTTPRequestHandler):
        def answer(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            state.seen.append((self.command, self.path, body))
            page = f"<html><body><h1>Gateway failure {state.status}</h1></body></html>".encode()
            self.send_response(state.status)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("X-Request-ID", f"synthetic-gateway-{state.status}")
            self.end_headers()
            self.wfile.write(page)

        do_GET = do_POST = do_DELETE = answer  # noqa: N815 - upstream handler names

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _bea(tmp_path: Path, gateway: Gateway, operation: str, *, as_json: bool) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_bytes(LEDGER)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_")
        and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
        and not key.lower().endswith("_proxy")
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        BEA_API_URL=gateway.url,
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    if operation == "logout":
        credential = tmp_path / "config" / "credentials.json"
        credential.parent.mkdir()
        credential.write_text(json.dumps({"token": "synthetic-stored-token", "expireAt": "2099-01-01T00:00:00+00:00"}))
    else:
        env["BEA_TOKEN"] = "synthetic-environment-token"
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if as_json else []), "--yes", *COMMANDS[operation]],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _error(done: subprocess.CompletedProcess[str], *, status: int, as_json: bool, code: int) -> str:
    assert done.returncode == code, done.stdout + done.stderr
    assert done.stdout == ""
    request_id = f"synthetic-gateway-{status}"
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == ("conflict" if code == 4 else "validation")
        assert error["exit_code"] == code
        assert error["request_id"] == request_id
        message = error["message"]
    else:
        assert f"Request ID: {request_id}" in done.stderr
        message = " ".join(done.stderr.split())
    assert f"HTTP {status}" in message
    assert "<html>" not in message and "GatewayTimeout" not in message
    return message


def _assert_one_request_and_local_effects(tmp_path: Path, gateway: Gateway, operation: str) -> None:
    assert len(gateway.seen) == 1, "the CLI must make one attempt, without automatically retrying"
    method, path, body = gateway.seen[0]
    assert (method, urlsplit(path).path) == REQUESTS[operation]
    if operation == "create":
        assert json.loads(body)["name"] == "newbook"
    assert (tmp_path / "main.bean").read_bytes() == LEDGER
    if operation == "logout":
        assert not (tmp_path / "config" / "credentials.json").exists()


@pytest.mark.parametrize("status", [521, 523, 522])
@pytest.mark.parametrize("operation", ["create", "delete", "logout"])
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_gateway_connection_status_preserves_what_is_known_about_the_write(
    tmp_path: Path, gateway: Gateway, status: int, operation: str, as_json: bool
) -> None:
    gateway.status = status

    done = _bea(tmp_path, gateway, operation, as_json=as_json)

    message = _error(done, status=status, as_json=as_json, code=4 if status == 522 else 1)
    if status == 522:
        # Cloudflare 522 covers both a pre-TCP timeout and a resource-request ACK timeout after TCP connects.
        assert "outcome is unknown" in message.lower()
        assert "Could not reach the server" not in message
    else:
        assert "Could not reach the server" in message
        assert "outcome is unknown" not in message.lower()
    assert "the request arrived" not in message.lower()
    if operation == "logout":
        assert "Removed the local credential" in message
        assert "session may still be valid" in message
    _assert_one_request_and_local_effects(tmp_path, gateway, operation)


@pytest.mark.parametrize(("status", "operation"), [(504, "create"), (520, "delete"), (524, "logout"), (504, "logout")])
def test_ambiguous_gateway_failures_still_report_an_unknown_write(
    tmp_path: Path, gateway: Gateway, status: int, operation: str
) -> None:
    gateway.status = status

    done = _bea(tmp_path, gateway, operation, as_json=True)

    message = _error(done, status=status, as_json=True, code=4)
    assert "outcome is unknown" in message.lower()
    assert "Could not reach the server" not in message
    assert "the request arrived" not in message.lower()
    if operation == "logout":
        assert "Removed the local credential" in message and "session may still be valid" in message
    else:
        assert "check the current state before retrying" in message
    _assert_one_request_and_local_effects(tmp_path, gateway, operation)


@pytest.mark.parametrize("status", [521, 523, 522, 504, 520, 524])
def test_gateway_failures_on_reads_stay_plain_failures(tmp_path: Path, gateway: Gateway, status: int) -> None:
    gateway.status = status

    done = _bea(tmp_path, gateway, "read", as_json=True)

    message = _error(done, status=status, as_json=True, code=1)
    assert "outcome is unknown" not in message.lower()
    assert ("Could not reach the server" in message) == (status in {521, 523})
    _assert_one_request_and_local_effects(tmp_path, gateway, "read")
