"""CONNECT setup failures sent no API write; a lost answer after tunneling stays unknown (w5/702)."""

from __future__ import annotations

import json
import os
import shutil
import socket
import socketserver
import ssl
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from cli.api import client as api_client
from cli.main import app

TOKEN = "synthetic-connect-phase-token"
LEDGER = b"2026-01-01 open Assets:Cash USD\n"
API_URL = "https://api.qa.invalid"
COMMANDS = {
    "create": ["cloud", "ledger", "create", "newbook"],
    "delete": ["cloud", "ledger", "delete", "qa/books"],
    "logout": ["cloud", "logout"],
}
ORIGIN_LINES = {
    "create": b"POST /api-gateway/v1/ledgers HTTP/1.1",
    "delete": b"DELETE /api-gateway/v1/ledgers/qa/books HTTP/1.1",
    "logout": b"POST /api-gateway/v1/logout HTTP/1.1",
}


@pytest.fixture(scope="module")
def local_tls(tmp_path_factory: pytest.TempPathFactory) -> tuple[ssl.SSLContext, Path]:
    directory = tmp_path_factory.mktemp("connect-proxy-tls")
    certificate = directory / "certificate.pem"
    key = directory / "key.pem"
    config = directory / "openssl.cnf"
    config.write_text(
        "[req]\nprompt = no\ndistinguished_name = dn\nx509_extensions = extensions\n"
        "[dn]\nCN = api.qa.invalid\n[extensions]\nsubjectAltName = DNS:api.qa.invalid\n"
        "basicConstraints = critical,CA:TRUE\nkeyUsage = digitalSignature,keyEncipherment,keyCertSign\n"
    )
    openssl = shutil.which("openssl")
    assert openssl is not None, "The local TLS proxy fixture needs the system openssl command"
    made = subprocess.run(
        [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-config",
            str(config),
            "-keyout",
            str(key),
            "-out",
            str(certificate),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert made.returncode == 0, made.stderr
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    return context, certificate


@dataclass
class Proxy:
    url: str = ""
    connects: list[bytes] = field(default_factory=list)
    origin_requests: list[bytes] = field(default_factory=list)
    errors: list[Exception] = field(default_factory=list)
    release: threading.Event = field(default_factory=threading.Event)


def _read_request(connection: socket.socket) -> bytes:
    data = b""
    while b"\r\n\r\n" not in data:
        part = connection.recv(65536)
        if not part:
            raise EOFError("Request ended before its headers")
        data += part
    headers, body = data.split(b"\r\n\r\n", 1)
    length = next(
        (int(line.split(b":", 1)[1]) for line in headers.split(b"\r\n") if line.lower().startswith(b"content-length:")),
        0,
    )
    while len(body) < length:
        part = connection.recv(65536)
        if not part:
            raise EOFError("Request ended before its body")
        body += part
    return headers + b"\r\n\r\n" + body


@contextmanager
def _proxy(mode: str, tls: ssl.SSLContext | None = None) -> Iterator[Proxy]:
    state = Proxy()

    class Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            try:
                self.request.settimeout(10)
                connect = _read_request(self.request)
                state.connects.append(connect.split(b"\r\n", 1)[0])
                if mode == "close" or (mode == "redirect" and len(state.connects) == 2):
                    return
                if mode == "malformed":
                    self.request.sendall(b"This is not an HTTP response\r\n\r\n")
                    return
                if mode == "unanswered":
                    state.release.wait(5)
                    return
                if mode == "407":
                    self.request.sendall(b"HTTP/1.1 407 Proxy Authentication Required\r\nContent-Length: 0\r\n\r\n")
                    return
                assert tls is not None
                self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                with tls.wrap_socket(self.request, server_side=True) as origin:
                    state.origin_requests.append(_read_request(origin))
                    if mode == "origin-timeout":
                        state.release.wait(5)
                    elif mode == "redirect":
                        origin.sendall(
                            b"HTTP/1.1 307 Temporary Redirect\r\n"
                            b"Location: https://second.qa.invalid/retry\r\nContent-Length: 0\r\n\r\n"
                        )
                    else:
                        assert mode == "origin-close"
            except Exception as exc:
                state.errors.append(exc)

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    # server_close joins every request thread, after release wakes an
    # unanswered CONNECT/origin handler. No sleeping stub outlives its test.
    server.daemon_threads = False
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    state.url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield state
    finally:
        state.release.set()
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert state.errors == [], state.errors


def _configure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    proxy: Proxy,
    *,
    operation: str,
    certificate: Path | None = None,
) -> None:
    for name in tuple(os.environ):
        if name.startswith("BEA_") or name.lower().endswith("_proxy"):
            monkeypatch.delenv(name)
    values = {
        "BEA_CONFIG_DIR": str(tmp_path / "config"),
        "BEA_API_URL": API_URL,
        "BEA_NO_UPDATE_NOTIFIER": "1",
        "BEA_UPDATE_API_URL": "http://127.0.0.1:9",
        "BEA_TAP_FORMULA_URL": "http://127.0.0.1:9/bea.rb",
        "HTTPS_PROXY": proxy.url,
        "NO_PROXY": "",
        "NO_COLOR": "1",
        "TERM": "dumb",
    }
    if operation != "logout":
        values["BEA_TOKEN"] = TOKEN
    if certificate is not None:
        values["SSL_CERT_FILE"] = str(certificate)
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(api_client, "DEFAULT_TIMEOUT", httpx.Timeout(1.0, connect=5.0))
    (tmp_path / "main.bean").write_bytes(LEDGER)
    if operation == "logout":
        credential = tmp_path / "config" / "credentials.json"
        credential.parent.mkdir()
        credential.write_text(json.dumps({"token": TOKEN, "expireAt": "2099-01-01T00:00:00+00:00"}))
        credential.chmod(0o600)


def _invoke(operation: str, *, as_json: bool, code: int) -> str:
    done = CliRunner().invoke(app, [*(["--json"] if as_json else []), "--yes", *COMMANDS[operation]])
    assert done.exit_code == code, done.output
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == ("conflict" if code == 4 else "validation")
        assert error["exit_code"] == code
        message = error["message"]
    else:
        message = " ".join(done.stderr.split())
    assert TOKEN not in done.stderr
    assert "Traceback" not in done.stderr
    return message


def _local_effects(tmp_path: Path, operation: str) -> None:
    assert (tmp_path / "main.bean").read_bytes() == LEDGER
    if operation == "logout":
        assert not (tmp_path / "config" / "credentials.json").exists()


@pytest.mark.parametrize("mode", ["close", "malformed", "unanswered", "407"])
@pytest.mark.parametrize("operation", COMMANDS)
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_a_connect_failure_before_the_api_request_is_a_plain_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, operation: str, as_json: bool
) -> None:
    with _proxy(mode) as proxy:
        _configure(tmp_path, monkeypatch, proxy, operation=operation)

        message = _invoke(operation, as_json=as_json, code=1)

        assert "Could not reach the server (ProxyError)" in message
        assert "outcome is unknown" not in message
        assert proxy.connects == [b"CONNECT api.qa.invalid:443 HTTP/1.1"]
        assert proxy.origin_requests == []
    _local_effects(tmp_path, operation)


@pytest.mark.parametrize("operation", COMMANDS)
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_a_tls_tunnel_that_received_the_write_but_closed_before_reply_stays_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    local_tls: tuple[ssl.SSLContext, Path],
    operation: str,
    as_json: bool,
) -> None:
    tls, certificate = local_tls
    with _proxy("origin-close", tls) as proxy:
        _configure(tmp_path, monkeypatch, proxy, operation=operation, certificate=certificate)

        message = _invoke(operation, as_json=as_json, code=4)

        assert "outcome is unknown" in message.lower()
        assert "Could not reach the server" not in message
        assert proxy.connects == [b"CONNECT api.qa.invalid:443 HTTP/1.1"]
        assert len(proxy.origin_requests) == 1
        assert proxy.origin_requests[0].startswith(ORIGIN_LINES[operation] + b"\r\n")
        assert f"Authorization: Bearer {TOKEN}\r\n".encode() in proxy.origin_requests[0]
        if operation == "create":
            assert json.loads(proxy.origin_requests[0].split(b"\r\n\r\n", 1)[1])["name"] == "newbook"
    _local_effects(tmp_path, operation)


def test_a_timeout_after_the_tls_origin_received_the_write_stays_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local_tls: tuple[ssl.SSLContext, Path]
) -> None:
    tls, certificate = local_tls
    with _proxy("origin-timeout", tls) as proxy:
        _configure(tmp_path, monkeypatch, proxy, operation="create", certificate=certificate)

        message = _invoke("create", as_json=True, code=4)

        assert "outcome is unknown" in message.lower() and "Could not reach the server" not in message
        assert len(proxy.origin_requests) == 1
        assert proxy.origin_requests[0].startswith(ORIGIN_LINES["create"] + b"\r\n")
    _local_effects(tmp_path, "create")


def test_an_origin_request_before_a_redirect_to_a_new_failed_tunnel_stays_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local_tls: tuple[ssl.SSLContext, Path]
) -> None:
    tls, certificate = local_tls
    with _proxy("redirect", tls) as proxy:
        _configure(tmp_path, monkeypatch, proxy, operation="create", certificate=certificate)
        with api_client.bearer_client(TOKEN).get_httpx_client() as client:
            client.follow_redirects = True

            with pytest.raises(httpx.RemoteProtocolError):
                client.post(f"{API_URL}/api-gateway/v1/ledgers", json={"name": "newbook"})

        assert proxy.connects == [
            b"CONNECT api.qa.invalid:443 HTTP/1.1",
            b"CONNECT second.qa.invalid:443 HTTP/1.1",
        ]
        assert len(proxy.origin_requests) == 1
        assert proxy.origin_requests[0].startswith(ORIGIN_LINES["create"] + b"\r\n")


def test_the_callers_trace_and_other_extensions_survive_proxy_tracking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    observed_extensions: list[object] = []

    def trace(name: str, info: dict[str, Any]) -> None:
        events.append(name)

    extensions = {"trace": trace, "test-extension": "retained"}
    with _proxy("close") as proxy:
        _configure(tmp_path, monkeypatch, proxy, operation="create")
        with api_client.bearer_client(TOKEN).get_httpx_client() as client:
            client.event_hooks["request"].append(
                lambda request: observed_extensions.append(request.extensions.get("test-extension"))
            )

            with pytest.raises(httpx.ProxyError):
                client.request("POST", f"{API_URL}/api-gateway/v1/ledgers", extensions=extensions)

        assert "http11.send_request_headers.started" in events
        assert "http11.receive_response_headers.failed" in events
        assert observed_extensions == ["retained"]
        assert extensions == {"trace": trace, "test-extension": "retained"}
