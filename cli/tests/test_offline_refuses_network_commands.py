"""Global `--offline` refuses `bea cloud` and `bea ask` before any request (w5/515).

The cloud commands never read the flag, so `bea --offline -y cloud ledger
delete` sent the DELETE with exit 0, though `--offline` means no network and
`price refresh` already refuses it.
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
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


class _Recorder(BaseHTTPRequestHandler):
    seen: list[str] = []

    def _answer(self) -> None:
        type(self).seen.append(f"{self.command} {self.path}")
        body = json.dumps({"ok": True, "data": {"items": [], "total": 0}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_DELETE = _answer  # noqa: N815 - BaseHTTPRequestHandler's spelling

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def stub() -> Iterator[str]:
    _Recorder.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Recorder)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _bea(tmp_path: Path, stub: str, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_API_URL=stub,
        BEA_TOKEN="test-token",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (("--json", "-y", "cloud", "ledger", "delete", "qa/books"), "bea cloud requires network access"),
        (("cloud", "ledger", "create", "newbook"), "bea cloud requires network access"),
        (("cloud", "ledger", "list"), "bea cloud requires network access"),
        (("cloud", "logout"), "bea cloud logout requires network access"),
        (("-f", "main.bean", "ask", "--print", "q"), "bea ask requires network access"),
    ],
    ids=["delete", "create", "list", "logout", "ask"],
)
def test_offline_refuses_before_any_request(tmp_path: Path, stub: str, args: tuple[str, ...], named: str) -> None:
    result = _bea(tmp_path, stub, "--offline", *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert named in result.stdout + result.stderr
    assert "remove --offline" in result.stdout + result.stderr
    assert _Recorder.seen == []


def test_the_stub_answers_without_offline(tmp_path: Path, stub: str) -> None:
    _bea(tmp_path, stub, "cloud", "ledger", "list")

    assert _Recorder.seen, "the control must reach the stub"


def test_help_still_answers_offline(tmp_path: Path, stub: str) -> None:
    result = _bea(tmp_path, stub, "--offline", "cloud", "ledger", "list", "--help")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _Recorder.seen == []
