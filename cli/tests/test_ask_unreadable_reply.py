"""A 200 the AI SDK cannot read gets the unexpected-response sentence, not a Python message (w5/373).

An empty `choices` array raised `IndexError` in the SDK's response handling,
and an empty or truncated JSON body `JSONDecodeError` in its parser; both
printed as `Error: list index out of range` / `Expecting value: …`. The proxy
here is a localhost simulation; what is pinned is how `bea ask` reacts.
"""

from __future__ import annotations

import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from tests.test_into_glob_create import _env

EMPTY_CHOICES = b'{"id":"x","object":"chat.completion","created":1,"model":"gpt-4o","choices":[]}'


@pytest.mark.parametrize(
    "body",
    [EMPTY_CHOICES, b"", EMPTY_CHOICES[:60], b"<html>gateway</html>"],
    ids=["empty-choices", "empty-body", "truncated-json", "html-as-json"],
)
def test_ask_print_reports_an_unreadable_reply_in_the_cli_s_words(tmp_path: Path, body: bytes) -> None:
    ledger = tmp_path / "main.bean"
    original = b'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n'
    ledger.write_bytes(original)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    env = _env(tmp_path)
    env.update(
        BEA_TOKEN="synthetic-ask-token",
        BEA_API_URL=f"http://127.0.0.1:{server.server_port}",
        NO_PROXY="127.0.0.1,localhost",
    )
    try:
        result = subprocess.run(
            [sys.executable, "-m", "cli.main", "--file", str(ledger), "ask", "--print", "What is my balance?"],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert result.returncode == 1, result.stderr
    assert result.stdout == ""
    stderr = " ".join(result.stderr.split())
    assert "Unexpected server response (HTTP 200) from the assistant; nothing was written to your ledger." in stderr
    for leaked in ("list index out of range", "Expecting", "JSONDecodeError", "IndexError", "gateway"):
        assert leaked not in result.stderr
    assert ledger.read_bytes() == original
