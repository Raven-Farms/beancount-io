"""A stored credential that cannot be used never stops a local command (w5/589).

Every engine launch reads `credentials.json` for managed price fetches. The
read blocked forever on a FIFO, grew without bound on a link to `/dev/zero`,
and deeply nested JSON escaped as a raw recursion error that failed `check`
and `balance`. Cloud commands name such a file as unusable, and `cloud
logout` removes it. When the removal itself fails, logout says so without
advising the command that just failed, and still reports the revocation.
"""

from __future__ import annotations

import json
import os
import socketserver
import stat
import subprocess
import sys
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """\
2026-01-01 open Assets:Cash
2026-01-01 open Equity:Opening
2026-01-02 * "opening"
  Assets:Cash  1 USD
  Equity:Opening
"""
VALID = {"token": "stored-token-value", "expireAt": "2099-01-01T00:00:00+00:00"}
#: Deep enough to exhaust the JSON decoder's recursion, small enough to be read.
NESTED = "[" * 20000 + "]" * 20000

pytestmark = pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX file types")


def _fifo(path: Path) -> None:
    os.mkfifo(path)


def _dev_zero(path: Path) -> None:
    path.symlink_to("/dev/zero")


def _nested(path: Path) -> None:
    path.write_text(NESTED)


def _directory(path: Path) -> None:
    path.mkdir()


def _oversized(path: Path) -> None:
    path.write_text(json.dumps({**VALID, "padding": "x" * 100_000}))


STORED: dict[str, tuple[Callable[[Path], None], str]] = {
    "fifo": (_fifo, "it is not a regular file"),
    "dev-zero": (_dev_zero, "it is not a regular file"),
    "nested-json": (_nested, "it is not valid JSON"),
    "directory": (_directory, "it is not a regular file"),
    "oversized": (_oversized, "it is larger than 64 KiB"),
}


def _bea(
    tmp_path: Path, *args: str, config: Path | None = None, url: str = "http://127.0.0.1:9"
) -> subprocess.CompletedProcess[str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("BEA_") and k != "CI" and not k.lower().endswith("_proxy")
    }
    env.update(
        BEA_CONFIG_DIR=str(config or tmp_path / "cfg"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_API_URL=url,
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    # The timeout is the hang detector: before the fix a FIFO never returned.
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _stored(tmp_path: Path, case: str) -> Path:
    config = tmp_path / "cfg"
    config.mkdir(mode=stat.S_IRWXU)
    (tmp_path / "main.bean").write_text(LEDGER)
    stored = config / "credentials.json"
    STORED[case][0](stored)
    return stored


def _message(result: subprocess.CompletedProcess[str]) -> str:
    return " ".join((result.stdout + result.stderr).split())


@pytest.mark.parametrize("case", sorted(STORED))
def test_local_reads_answer_and_cloud_status_names_the_file(tmp_path: Path, case: str) -> None:
    stored = _stored(tmp_path, case)

    balance = _bea(tmp_path, "-f", str(tmp_path / "main.bean"), "balance")
    assert balance.returncode == 0, balance.stderr
    assert "Cash" in balance.stdout

    status = _bea(tmp_path, "cloud", "status")
    assert status.returncode == 3, status.stdout + status.stderr
    message = _message(status)
    assert f"The stored credential {stored} is unusable: {STORED[case][1]}" in message
    assert "recursion" not in message


@pytest.mark.parametrize("case", ["fifo", "nested-json"])
def test_check_and_json_balance_answer(tmp_path: Path, case: str) -> None:
    _stored(tmp_path, case)

    check = _bea(tmp_path, "-f", str(tmp_path / "main.bean"), "check")
    assert check.returncode == 0, check.stderr

    balance = _bea(tmp_path, "--json", "-f", str(tmp_path / "main.bean"), "balance")
    assert balance.returncode == 0, balance.stderr
    assert json.loads(balance.stdout)["data"]["as_of"] == "2026-01-02"


@pytest.mark.parametrize("case", ["fifo", "dev-zero", "nested-json"])
def test_logout_removes_an_unusable_file(tmp_path: Path, case: str) -> None:
    stored = _stored(tmp_path, case)

    logout = _bea(tmp_path, "cloud", "logout")

    assert logout.returncode == 1, logout.stdout + logout.stderr
    assert f"Removed the unusable credential file {stored}" in _message(logout)
    assert not os.path.lexists(stored)
    assert os.path.exists("/dev/zero")


def test_logout_that_cannot_remove_a_directory_does_not_advise_logout(tmp_path: Path) -> None:
    stored = _stored(tmp_path, "directory")

    logout = _bea(tmp_path, "cloud", "logout")

    assert logout.returncode == 1, logout.stdout + logout.stderr
    message = _message(logout)
    assert f"The stored credential {stored} is unusable (it is not a regular file) and could not be removed" in message
    assert "Remove it yourself." in message
    assert "cloud logout" not in message
    assert stored.is_dir()


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes into a mode-500 directory")
def test_logout_in_a_read_only_directory_does_not_advise_logout(tmp_path: Path) -> None:
    stored = _stored(tmp_path, "nested-json")
    stored.parent.chmod(0o500)
    try:
        logout = _bea(tmp_path, "cloud", "logout")
    finally:
        stored.parent.chmod(stat.S_IRWXU)

    assert logout.returncode == 1, logout.stdout + logout.stderr
    message = _message(logout)
    assert f"{stored} is unusable (it is not valid JSON) and could not be removed: Permission denied" in message
    assert "cloud logout" not in message
    assert stored.exists()


def test_a_config_dir_that_is_a_file_is_named_as_such(tmp_path: Path) -> None:
    status = _bea(tmp_path, "cloud", "status", config=Path(os.devnull))

    assert status.returncode == 3, status.stdout + status.stderr
    message = _message(status)
    assert f"The bea configuration directory {os.devnull} is not a directory" in message
    assert "BEA_CONFIG_DIR" in message
    assert "NotADirectoryError" not in message


class _Revocation(socketserver.StreamRequestHandler):
    answer = b""
    received: list[bytes] = []

    def handle(self) -> None:
        request = self.rfile.readline()
        length = 0
        while (line := self.rfile.readline()) not in (b"\r\n", b"\n", b""):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1])
        self.rfile.read(length)
        type(self).received.append(request)
        self.wfile.write(type(self).answer)


@pytest.fixture
def server() -> Iterator[str]:
    _Revocation.received = []
    stub = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Revocation)
    stub.daemon_threads = True
    threading.Thread(target=stub.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{stub.server_address[1]}"
    finally:
        stub.shutdown()
        stub.server_close()


def _answer(status: str, body: dict[str, object]) -> bytes:
    payload = json.dumps(body).encode()
    return (
        f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n"
        "Connection: close\r\n\r\n"
    ).encode() + payload


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes into a mode-500 directory")
@pytest.mark.parametrize(
    ("answer", "outcome"),
    [
        (
            _answer("200 OK", {"success": True}),
            "Revoked the session on the server, but could not remove the local credential",
        ),
        (
            _answer("500 Internal Server Error", {"success": False, "message": "boom"}),
            "Also, server revocation failed",
        ),
    ],
    ids=["revoked", "revocation-failed"],
)
def test_a_valid_credential_that_cannot_be_removed_reports_the_revocation(
    tmp_path: Path, server: str, answer: bytes, outcome: str
) -> None:
    config = tmp_path / "cfg"
    config.mkdir(mode=stat.S_IRWXU)
    stored = config / "credentials.json"
    stored.write_text(json.dumps(VALID))
    config.chmod(0o500)
    _Revocation.answer = answer
    try:
        logout = _bea(tmp_path, "--json", "cloud", "logout", url=server)
    finally:
        config.chmod(stat.S_IRWXU)

    assert logout.returncode == 1, logout.stdout + logout.stderr
    assert len(_Revocation.received) == 1 and _Revocation.received[0].startswith(b"POST ")
    message = json.loads(logout.stdout or logout.stderr)["error"]["message"]
    assert outcome in message
    assert f"{stored} (Permission denied)" in message
    assert "Removed the local credential" not in message
    assert "Errno" not in message
    assert stored.exists()
