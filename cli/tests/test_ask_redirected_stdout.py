"""`bea ask > out.txt` at a terminal refuses instead of drawing its session into the file (w5/550).

The session draws its prompt and its write-approval panel on stdout. With
stdout redirected the person saw nothing, the file collected the panel, and
a blind `y` Enter still approved the AI's write.
"""

from __future__ import annotations

import os
import pty
import select
import sys
import time
from pathlib import Path

from tests.conftest import CLI_ROOT, StubModel


def test_a_redirected_session_exits_2_naming_print(tmp_path: Path, stub_model: StubModel) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n', encoding="utf-8")
    out = tmp_path / "out.txt"
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_NO_ASK_HISTORY="1",
        BEA_API_URL=stub_model.url,
        BEA_TOKEN="stub-token",
        PYTHONPATH=str(CLI_ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover - replaced by exec in the child
        os.chdir(tmp_path)
        redirected = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.dup2(redirected, 1)
        os.execve(sys.executable, [sys.executable, "-m", "cli.main", "--file", str(ledger), "ask"], env)
    screen = b""
    deadline = time.time() + 60
    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if ready:
                try:
                    screen += os.read(fd, 65536)
                except OSError:
                    pass
            finished, status = os.waitpid(pid, os.WNOHANG)
            if finished:
                break
            assert time.time() < deadline, f"bea ask never exited; terminal showed {screen!r}"
    finally:
        os.close(fd)

    assert os.waitstatus_to_exitcode(status) == 2, screen
    shown = " ".join(screen.decode("utf-8", "replace").split())
    assert "stdout is redirected" in shown and "--print" in shown, shown
    assert out.read_text(encoding="utf-8") == ""
    assert stub_model.count == 0
