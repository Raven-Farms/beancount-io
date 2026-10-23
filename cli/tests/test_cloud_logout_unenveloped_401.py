"""`cloud logout` takes any 401 as already revoked, envelope or not (w5/812).

A 401 whose JSON body lacked the `{ok, error}` envelope — a proxy's or a
framework's `{"message": "Unauthorized"}`, `{"error": …}`, `[]` — was mapped
to an authorization error inside the client, so logout's own "a 401 means
already revoked" check never saw it: exit 1, "server revocation failed".
"""

from __future__ import annotations

import json
import os
import socketserver
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS = {"token": "stored-token-value", "expireAt": "2027-01-01T00:00:00+00:00"}


def _answer(status: str, body: bytes) -> bytes:
    head = f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n"
    return head.encode() + b"Connection: close\r\n\r\n" + body


class _Server(socketserver.StreamRequestHandler):
    answer = b""

    def handle(self) -> None:
        length = 0
        while (line := self.rfile.readline()) not in (b"\r\n", b"\n", b""):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1])
        self.rfile.read(length)
        self.wfile.write(type(self).answer)


@pytest.fixture
def server() -> Iterator[str]:
    stub = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Server)
    stub.daemon_threads = True
    threading.Thread(target=stub.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{stub.server_address[1]}"
    finally:
        stub.shutdown()
        stub.server_close()


def _logout(tmp_path: Path, url: str, *flags: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "credentials.json").write_text(json.dumps(CREDENTIALS))
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("BEA_") and k != "CI" and not k.lower().endswith("_proxy")
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_API_URL=url,
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *flags, "cloud", "logout"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize(
    "body",
    [b'{"message": "Unauthorized"}', b'{"error": "unauthorized"}', b"[]"],
    ids=["message", "error-string", "array"],
)
def test_an_unenveloped_401_is_already_revoked(tmp_path: Path, server: str, body: bytes) -> None:
    _Server.answer = _answer("401 Unauthorized", body)

    result = _logout(tmp_path, server)

    assert result.returncode == 0, result.stderr
    assert "Logged out." in result.stdout + result.stderr
    assert "revocation failed" not in result.stderr
    assert not (tmp_path / "config" / "credentials.json").exists()


def test_an_unenveloped_403_is_still_a_failed_revocation(tmp_path: Path, server: str) -> None:
    _Server.answer = _answer("403 Forbidden", b'{"message": "Forbidden"}')

    result = _logout(tmp_path, server)

    assert result.returncode != 0
    assert "server revocation failed" in " ".join(result.stderr.split())
