"""`bea query > out.txt` at a terminal refuses the shell instead of opening it invisibly (w5/587).

Upstream's `input()` draws the prompt on stdout. With stdout redirected the
terminal stayed blank for the whole session, and the results file collected
the `beanquery>` prompts.
"""

from __future__ import annotations

import os
import pty
import select
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "args", [["-f", "main.bean", "query"], ["query", "--source", "main.bean"]], ids=["file", "source"]
)
def test_a_redirected_shell_exits_2_and_writes_nothing(tmp_path: Path, args: list[str]) -> None:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n')
    out = tmp_path / "out.txt"
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        HOME=str(tmp_path / "home"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover - replaced by exec in the child
        os.chdir(tmp_path)
        redirected = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.dup2(redirected, 1)
        os.execve(sys.executable, [sys.executable, "-m", "cli.main", *args], env)
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
            assert time.time() < deadline, f"the shell opened invisibly; the terminal showed {screen!r}"
    finally:
        os.close(fd)

    assert os.waitstatus_to_exitcode(status) == 2, screen
    assert "The query shell draws its prompt on stdout, and stdout is redirected" in " ".join(
        screen.decode("utf-8", "replace").split()
    )
    assert out.read_text() == ""
