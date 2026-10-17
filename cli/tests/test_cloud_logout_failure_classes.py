"""`cloud logout` keeps the credential on a bad API URL and calls a lost answer unknown (w5/521).

One broad `except` around building the client and the call deleted the
credential on a malformed BEA_API_URL without trying to revoke it, and
reported a revocation the server received but never answered as "Could not
reach the server" (exit 1).
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


class _Server(socketserver.StreamRequestHandler):
    answer: bytes | None = None

    def handle(self) -> None:
        length = 0
        while (line := self.rfile.readline()) not in (b"\r\n", b"\n", b""):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1])
        self.rfile.read(length)
        if type(self).answer is not None:
            self.wfile.write(type(self).answer)
        # With no answer the connection just closes: the request arrived.


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


def _logout(tmp_path: Path, url: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "--json", "cloud", "logout"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_a_malformed_url_keeps_the_credential(tmp_path: Path) -> None:
    result = _logout(tmp_path, "htps://api.example.invalid")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "Removed the local credential" not in result.stdout + result.stderr
    assert (tmp_path / "config" / "credentials.json").exists()


@pytest.mark.parametrize(
    "answer",
    [None, b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK"],
    ids=["closed-after-the-post", "unreadable-200"],
)
def test_a_lost_answer_is_an_unknown_outcome(tmp_path: Path, server: str, answer: bytes | None) -> None:
    _Server.answer = answer

    result = _logout(tmp_path, server)

    assert result.returncode == 4, result.stdout + result.stderr
    message = json.loads(result.stdout or result.stderr)["error"]["message"]
    assert "the outcome is unknown" in message
    assert "Could not reach the server" not in message
    assert not (tmp_path / "config" / "credentials.json").exists()


def test_a_refused_connection_stays_a_plain_failure(tmp_path: Path) -> None:
    result = _logout(tmp_path, "http://127.0.0.1:9")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Could not reach the server" in result.stdout + result.stderr


def test_a_bodiless_204_logs_out(tmp_path: Path, server: str) -> None:
    _Server.answer = b"HTTP/1.1 204 No Content\r\n\r\n"

    result = _logout(tmp_path, server)

    assert result.returncode == 0, result.stdout + result.stderr
