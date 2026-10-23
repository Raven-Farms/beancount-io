"""Malformed BEA_TOKEN advice follows its source, and logout never uses that token (w5/703)."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

TOKENS = [
    pytest.param("synthetic bad token", id="space"),
    pytest.param("synthetic-token\n", id="control"),
    pytest.param("synthetic-tök", id="non-ascii"),
]
BROKEN_STORED = b"not JSON; do not inspect or replace this shadowed stored credential\n"
LEDGER = b"2026-01-01 open Assets:Cash USD\n"


@dataclass
class TokenServer:
    url: str = ""
    requests: list[tuple[str, str, str | None]] = field(default_factory=list)


@pytest.fixture
def token_server() -> Iterator[TokenServer]:
    state = TokenServer()

    class Handler(BaseHTTPRequestHandler):
        def answer(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            state.requests.append((self.command, self.path, self.headers.get("Authorization")))
            self.send_response(204)
            self.end_headers()

        do_GET = do_POST = answer  # noqa: N815

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.url = f"http://127.0.0.1:{server.server_port}"
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
        assert not worker.is_alive()


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token_server: TokenServer, token: str) -> Path:
    for name in tuple(os.environ):
        if name.startswith("BEA_") or name.lower().endswith("_proxy"):
            monkeypatch.delenv(name)
    credential = tmp_path / "config" / "credentials.json"
    credential.parent.mkdir()
    credential.write_bytes(BROKEN_STORED)
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(LEDGER)
    for name, value in {
        "BEA_CONFIG_DIR": str(credential.parent),
        "BEA_TOKEN": token,
        "BEA_API_URL": token_server.url,
        "BEA_FILE": str(ledger),
        "BEA_NO_UPDATE_NOTIFIER": "1",
        "BEA_UPDATE_API_URL": "http://127.0.0.1:9",
        "BEA_TAP_FORMULA_URL": "http://127.0.0.1:9/bea.rb",
        "NO_PROXY": "*",
        "NO_COLOR": "1",
        "TERM": "dumb",
    }.items():
        monkeypatch.setenv(name, value)
    return credential


def _invoke(args: list[str], *, as_json: bool) -> Any:
    return CliRunner().invoke(app, [*(["--json"] if as_json else []), *args])


def _unchanged(tmp_path: Path, credential: Path, token_server: TokenServer) -> None:
    assert credential.read_bytes() == BROKEN_STORED
    assert (tmp_path / "main.bean").read_bytes() == LEDGER
    assert token_server.requests == []


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_logout_is_a_noop_even_for_a_malformed_environment_token_and_broken_stored_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token_server: TokenServer, token: str, as_json: bool
) -> None:
    credential = _setup(tmp_path, monkeypatch, token_server, token)

    done = _invoke(["cloud", "logout"], as_json=as_json)

    assert done.exit_code == 0, done.output
    assert done.stderr == ""
    if as_json:
        assert done.stdout == ""
    else:
        assert "BEA_TOKEN is set in this shell" in done.stdout
        assert "leaves it unchanged and does not revoke it" in done.stdout
        assert "Unset BEA_TOKEN" in done.stdout
    assert token not in done.output
    _unchanged(tmp_path, credential, token_server)


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("command", ["status", "ledger", "ask"])
def test_authenticating_commands_only_propose_fixing_the_active_environment_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token_server: TokenServer, token: str, command: str
) -> None:
    credential = _setup(tmp_path, monkeypatch, token_server, token)
    args = {
        "status": ["cloud", "status"],
        "ledger": ["cloud", "ledger", "list"],
        "ask": ["ask", "--print", "Hello."],
    }[command]
    as_json = command == "ledger"

    done = _invoke(args, as_json=as_json)

    assert done.exit_code == 3, done.output
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "auth" and error["exit_code"] == 3
        message = error["message"]
    else:
        message = " ".join(done.stderr.split())
    assert "Invalid BEA_TOKEN" in message and "Fix or unset BEA_TOKEN" in message
    assert "bea cloud login" not in message and "stored credential" not in message
    assert token not in done.output
    _unchanged(tmp_path, credential, token_server)


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_login_still_requires_unsetting_the_malformed_environment_token_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token_server: TokenServer, token: str, as_json: bool
) -> None:
    credential = _setup(tmp_path, monkeypatch, token_server, token)

    done = _invoke(["cloud", "login"], as_json=as_json)

    assert done.exit_code == 2, done.output
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "usage" and error["exit_code"] == 2
        message = error["message"]
    else:
        message = " ".join(done.stderr.split())
    assert "BEA_TOKEN is set in this shell" in message and "Unset BEA_TOKEN first" in message
    assert "Invalid BEA_TOKEN" not in message
    assert token not in done.output
    _unchanged(tmp_path, credential, token_server)


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_an_empty_environment_token_still_revokes_the_stored_credential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token_server: TokenServer, as_json: bool
) -> None:
    credential = _setup(tmp_path, monkeypatch, token_server, "")
    credential.write_text(json.dumps({"token": "synthetic-stored-token", "expireAt": "2099-01-01T00:00:00Z"}))

    done = _invoke(["cloud", "logout"], as_json=as_json)

    assert done.exit_code == 0, done.output
    assert token_server.requests == [("POST", "/api-gateway/v1/logout", "Bearer synthetic-stored-token")]
    assert not credential.exists()
    assert (tmp_path / "main.bean").read_bytes() == LEDGER
    assert "BEA_TOKEN is set" not in done.output


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_an_empty_environment_token_without_a_stored_file_is_already_logged_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token_server: TokenServer, as_json: bool
) -> None:
    credential = _setup(tmp_path, monkeypatch, token_server, "")
    credential.unlink()

    done = _invoke(["cloud", "logout"], as_json=as_json)

    assert done.exit_code == 0, done.output
    assert done.stderr == ""
    if not as_json:
        assert "Already logged out." in done.stdout
    assert not credential.exists() and token_server.requests == []


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_a_valid_environment_token_keeps_the_same_logout_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token_server: TokenServer, as_json: bool
) -> None:
    credential = _setup(tmp_path, monkeypatch, token_server, "synthetic-valid-token")

    done = _invoke(["cloud", "logout"], as_json=as_json)

    assert done.exit_code == 0, done.output
    assert done.stderr == ""
    if not as_json:
        assert "leaves it unchanged and does not revoke it" in done.stdout
    _unchanged(tmp_path, credential, token_server)
