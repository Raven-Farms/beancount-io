"""Ask reports HTTP redirects like cloud commands, without following them (w5/679)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import openai
import pytest
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError

from cli.ask.agent import BqlDeps, translated_failures
from cli.errors import BeaError

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "synthetic-redirect-test-token"
LEDGER = b'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


def _env(tmp_path: Path, base_url: str) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_TOKEN=TOKEN,
        BEA_API_URL=base_url,
        PYTHONPATH=str(ROOT / "src"),
        NO_PROXY="127.0.0.1,localhost",
        no_proxy="127.0.0.1,localhost",
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


@pytest.mark.parametrize(
    ("status", "location"),
    [(301, True), (302, True), (303, True), (307, True), (308, True), (307, False)],
    ids=["301", "302", "303", "307", "308", "no-location"],
)
def test_real_ask_and_cloud_http_redirects_are_named_and_never_followed(
    tmp_path: Path, status: int, location: bool
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(LEDGER)
    requests: list[tuple[str, str, str | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def respond(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            requests.append((self.command, self.path, self.headers.get("Authorization")))
            self.send_response(status)
            if location:
                self.send_header("Location", f"{base_url}/portal/login?session=redirect-secret#fragment-secret")
            self.send_header("X-Request-Id", "req-redirect-test")
            self.send_header("x-should-retry", "false")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            self.respond()

        def do_GET(self) -> None:  # noqa: N802
            self.respond()

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    base_url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    commands = [
        (["ask", "What is my balance?", "--print"], "POST", "/api-gateway/ai/openai/chat/completions"),
        (["cloud", "status"], "GET", "/api-gateway/v1/user-profile"),
    ]
    try:
        for command, method, endpoint in commands:
            requests.clear()
            result = subprocess.run(
                [sys.executable, "-m", "cli.main", "--no-input", "--file", str(ledger), *command],
                env=_env(tmp_path, base_url),
                cwd=tmp_path,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert requests == [(method, endpoint, f"Bearer {TOKEN}")], requests
            assert result.returncode == 1, result.stdout + result.stderr
            assert result.stdout == ""
            shown = " ".join(result.stderr.split())
            target = f" to {base_url}/portal/login" if location else ""
            assert f"Unexpected redirect (HTTP {status}){target}; bea does not follow redirects." in shown, shown
            assert "BEA_API_URL" in shown and "proxy or captive portal" in shown, shown
            for leaked in (
                "redirect-secret",
                "fragment-secret",
                TOKEN,
                "Could not reach",
                "Not authorized",
                "BEA_TOKEN",
                "bea cloud login",
                "mint a new token",
                "ModelAPIError",
                "APIStatusError",
                "HTTPStatusError",
                "status_code",
                "model_name",
                "Traceback",
            ):
                assert leaked not in result.stderr, result.stderr
            assert ledger.read_bytes() == LEDGER
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _status_error(kind: str, status: int, *, location: bool = True) -> BaseException:
    headers = {"X-Request-Id": "req-wrapped-status"}
    if location:
        headers["Location"] = "https://portal.example/login?session=unit-secret#unit-fragment"
    request = httpx.Request("POST", "https://api.example/completions")
    body = {"message": "server sentence"}
    response = httpx.Response(status, headers=headers, json=body, request=request)
    if kind == "openai":
        return openai.APIStatusError("sdk-private-message", response=response, body=body)
    return httpx.HTTPStatusError("sdk-private-message", request=request, response=response)


@pytest.mark.parametrize("kind", ["openai", "httpx"])
@pytest.mark.parametrize("link", ["cause", "context"])
def test_wrapped_redirect_keeps_request_id_and_actual_writes(tmp_path: Path, kind: str, link: str) -> None:
    outer = ModelAPIError("private-model", "private-model-message")
    middle = RuntimeError("private-wrapper-message")
    status_error = _status_error(kind, 307)
    if link == "cause":
        outer.__cause__ = middle
        middle.__cause__ = status_error
    else:
        outer.__context__ = middle
        middle.__context__ = status_error
    deps = BqlDeps(file=tmp_path / "main.bean")

    with pytest.raises(BeaError) as caught:
        with translated_failures(deps):
            deps.writes.extend([(1, "/books/transactions.bean"), (2, "/books/transactions.bean")])
            raise outer

    error = caught.value
    assert error.exit_code == 1 and error.category == "validation"
    assert error.request_id == "req-wrapped-status"
    message = str(error)
    assert "Unexpected redirect (HTTP 307) to https://portal.example/login; bea does not follow redirects." in message
    assert "3 directive(s) to /books/transactions.bean" in message
    assert "which stay in your ledger" in message
    assert "nothing was written" not in message
    for leaked in ("private-", "unit-secret", "unit-fragment", "ModelAPIError", "APIStatusError", "HTTPStatusError"):
        assert leaked not in message


@pytest.mark.parametrize("with_headers", [False, True], ids=["no-headers", "headers"])
def test_direct_model_http_error_redirect_compatibility(tmp_path: Path, with_headers: bool) -> None:
    headers = (
        {"Location": "https://portal.example/login?session=unit-secret#unit-fragment", "X-Request-Id": "req-direct"}
        if with_headers
        else None
    )
    failure = ModelHTTPError(302, "private-model", {"message": "private-body"}, headers=headers)
    deps = BqlDeps(file=tmp_path / "main.bean")

    with pytest.raises(BeaError) as caught:
        with translated_failures(deps):
            deps.writes.append((1, "/books/main.bean"))
            raise failure

    error = caught.value
    assert error.exit_code == 1 and error.category == "validation"
    assert error.request_id == ("req-direct" if with_headers else None)
    target = " to https://portal.example/login" if with_headers else ""
    assert f"Unexpected redirect (HTTP 302){target}; bea does not follow redirects." in str(error)
    assert "1 directive(s) to /books/main.bean" in str(error) and "nothing was written" not in str(error)
    for leaked in ("private-", "unit-secret", "unit-fragment", "ModelHTTPError"):
        assert leaked not in str(error)


@pytest.mark.parametrize("kind", ["openai", "httpx"])
@pytest.mark.parametrize(
    ("status", "code", "category", "sentence"),
    [
        (401, 3, "auth", "Not authorized"),
        (409, 4, "conflict", "server sentence"),
        (429, 1, "validation", "Rate limited"),
        (503, 1, "validation", "Server error"),
    ],
)
def test_other_wrapped_http_statuses_keep_the_shared_mapping(
    kind: str, status: int, code: int, category: str, sentence: str
) -> None:
    outer = ModelAPIError("private-model", "private-message")
    outer.__cause__ = _status_error(kind, status, location=False)

    with pytest.raises(BeaError) as caught:
        with translated_failures():
            raise outer

    error = caught.value
    assert error.exit_code == code and error.category == category
    assert error.request_id == "req-wrapped-status"
    assert sentence in str(error) and "server sentence" in str(error)
    assert "Could not reach" not in str(error) and "private-" not in str(error)


def test_a_cyclic_wrapper_without_http_status_still_terminates_cleanly() -> None:
    outer = ModelAPIError("private-model", "private-message")
    inner = RuntimeError("private-inner")
    outer.__cause__ = inner
    inner.__context__ = outer

    with pytest.raises(BeaError) as caught:
        with translated_failures():
            raise outer

    assert "Could not reach the server" in str(caught.value)
    assert "private-" not in str(caught.value)


def test_a_genuine_transport_failure_remains_unreachable_and_keeps_actual_writes(tmp_path: Path) -> None:
    outer = ModelAPIError("private-model", "private-message")
    transport = httpx.ConnectError("transport-private-secret", request=httpx.Request("POST", "https://api.example"))
    outer.__cause__ = transport
    deps = BqlDeps(file=tmp_path / "main.bean")

    with pytest.raises(BeaError) as caught:
        with translated_failures(deps):
            deps.writes.append((1, "/books/main.bean"))
            raise outer

    message = str(caught.value)
    assert caught.value.exit_code == 1 and caught.value.request_id is None
    assert "Could not reach the server (ConnectError)." in message
    assert "1 directive(s) to /books/main.bean" in message and "nothing was written" not in message
    assert "private-" not in message and "Unexpected redirect" not in message
