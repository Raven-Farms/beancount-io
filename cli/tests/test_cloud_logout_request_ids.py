"""Logout retains HTTP request IDs when revocation has an unknown outcome (w5/701)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "synthetic-logout-request-id-token"
LEDGER = b"2026-01-01 open Assets:Cash USD\n"


@pytest.mark.parametrize(
    ("status", "header", "request_id", "exit_code"),
    [
        (200, "x-request-id", "req-unreadable-logout-701", 4),
        (524, "cf-ray", "8a1b2c3d4e-SJC", 4),
        (500, "x-request-id", "req-server-error-logout-701", 1),
    ],
    ids=["unreadable-success", "cloudflare-timeout", "ordinary-server-error"],
)
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_logout_keeps_the_servers_request_id_in_both_failure_outputs(
    tmp_path: Path, status: int, header: str, request_id: str, exit_code: int, as_json: bool
) -> None:
    requests: list[tuple[str, str, str | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            requests.append((self.command, self.path, self.headers.get("Authorization")))
            body = b"OK" if status == 200 else b"upstream error"
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.send_header(header, request_id)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    ledger = tmp_path / "main.bean"
    ledger.write_bytes(LEDGER)
    credential = tmp_path / "config" / "credentials.json"
    credential.parent.mkdir()
    credential.write_text(json.dumps({"token": TOKEN, "expireAt": "2099-01-01T00:00:00+00:00"}))
    credential.chmod(0o600)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_")
        and not key.lower().endswith("_proxy")
        and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    env.update(
        BEA_CONFIG_DIR=str(credential.parent),
        BEA_API_URL=f"http://127.0.0.1:{server.server_port}",
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        PYTHONPATH=str(ROOT / "src"),
        NO_PROXY="*",
        TERM="dumb",
        NO_COLOR="1",
    )
    try:
        done = subprocess.run(
            [sys.executable, "-m", "cli.main", *(["--json"] if as_json else []), "cloud", "logout"],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
        assert not worker.is_alive()

    assert done.returncode == exit_code, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == ("conflict" if exit_code == 4 else "validation")
        assert error["exit_code"] == exit_code
        assert error["request_id"] == request_id
        message = error["message"]
    else:
        assert f"Request ID: {request_id}" in done.stderr
        message = " ".join(done.stderr.split())
    assert "Removed the local credential" in message
    assert f"HTTP {status}" in message
    assert "session may still be valid" in message
    if exit_code == 4:
        assert "lost or unreadable" in message and "outcome is unknown" in message
    else:
        assert "server revocation failed" in message and "outcome is unknown" not in message
    assert requests == [("POST", "/api-gateway/v1/logout", f"Bearer {TOKEN}")]
    assert not credential.exists()
    assert ledger.read_bytes() == LEDGER
    assert TOKEN not in done.stdout + done.stderr
