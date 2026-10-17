"""A proxy that refuses the CONNECT tunnel is "could not reach the server", exit 1 (w5/519).

`httpx.ProxyError` fell into the unknown-outcome branch (exit 4, "check the
current state"), though the request never left the proxy and the read
through the same proxy already said it could not reach the server.
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


class _RefusingProxy(socketserver.StreamRequestHandler):
    seen: list[bytes] = []

    def handle(self) -> None:
        type(self).seen.append(self.rfile.readline())
        while self.rfile.readline() not in (b"\r\n", b"\n", b""):
            pass
        self.wfile.write(b"HTTP/1.1 407 Proxy Authentication Required\r\nContent-Length: 0\r\n\r\n")


@pytest.fixture
def proxy() -> Iterator[str]:
    _RefusingProxy.seen = []
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _RefusingProxy)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _bea(tmp_path: Path, proxy: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("BEA_") and k != "CI" and not k.lower().endswith("_proxy")
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_API_URL="https://api.qa.invalid",
        BEA_TOKEN="test-token-value",
        HTTPS_PROXY=proxy,
        NO_PROXY="",
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


@pytest.mark.parametrize(
    "args",
    [
        ("cloud", "ledger", "create", "newbook"),
        ("cloud", "ledger", "delete", "qa/books"),
        ("cloud", "ledger", "show", "qa/books"),
    ],
    ids=["create", "delete", "show"],
)
def test_a_refused_tunnel_could_not_reach_the_server(tmp_path: Path, proxy: str, args: tuple[str, ...]) -> None:
    result = _bea(tmp_path, proxy, *args)

    assert result.returncode == 1, result.stdout + result.stderr
    message = json.loads(result.stdout or result.stderr)["error"]["message"]
    assert message.startswith("Could not reach the server (ProxyError)")
    assert "outcome is unknown" not in message
    assert _RefusingProxy.seen and _RefusingProxy.seen[0].startswith(b"CONNECT api.qa.invalid:443")
