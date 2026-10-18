"""`cloud ledger create` refuses conflicting options before any request (w5/623).

`--private --public` created a public ledger (the last flag won), `-d a -d b`
kept `b`, and `--dir` without `--clone` created the ledger and cloned
nothing, unsaid. The help promises a mistyped flag cannot put someone's
finances on the open internet.
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

import pytest

ROOT = Path(__file__).resolve().parents[1]


class _Stub(BaseHTTPRequestHandler):
    received: list[str] = []

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        type(self).received.append(body.decode())
        payload = json.dumps(
            {
                "success": True,
                "data": {
                    "name": "qa-x",
                    "fullName": "me/qa-x",
                    "private": False,
                    "httpUrl": "https://x",
                    "sshUrl": "git@x:me/qa-x.git",
                },
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def stub() -> Iterator[str]:
    _Stub.received = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _create(tmp_path: Path, url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and not k.lower().endswith("_proxy")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_TOKEN="test-token",
        BEA_API_URL=url,
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "cloud", "ledger", "create", "qa-x", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
        check=False,
    )


@pytest.mark.parametrize(
    ("args", "said"),
    [
        (["--private", "--public"], "Pass --private or --public, not both"),
        (["-d", "a", "-d", "b"], "Conflicting values for one option: -d 'a' and -d 'b'"),
        (["--dir", "books"], "--dir is where --clone puts the new ledger; add --clone, or drop --dir"),
    ],
    ids=["visibility-pair", "two-descriptions", "dir-without-clone"],
)
def test_conflicting_options_are_refused_before_any_request(
    tmp_path: Path, stub: str, args: list[str], said: str
) -> None:
    result = _create(tmp_path, stub, *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert said in " ".join(result.stderr.split())
    assert _Stub.received == []


def test_one_visibility_flag_still_sends_the_request(tmp_path: Path, stub: str) -> None:
    """The control: the stub sees the create (its reply shape is not what this test is about)."""
    result = _create(tmp_path, stub, "--public")

    assert "not both" not in result.stderr
    (body,) = _Stub.received
    assert json.loads(body)["private"] is False
