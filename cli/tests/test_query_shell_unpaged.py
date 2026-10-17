"""The query shell prints results without a pager, as `bean-query` does (w5/585).

bea handed upstream's shell `sys.stdout` itself, which turns its pager on:
with `PAGER=less`, Ctrl-C interrupted the wait on `less` without ending it,
and the pager and the shell then split every keystroke.
"""

from __future__ import annotations

import fcntl
import os
import pty
import select
import shutil
import struct
import sys
import termios
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(shutil.which("less") is None, reason="needs less as the pager")


@pytest.mark.parametrize("term", ["dumb", None, "xterm-ghostty"], ids=["dumb", "unset", "unknown"])
def test_a_long_result_prints_whole_and_the_prompt_returns(tmp_path: Path, term: str | None) -> None:
    """With `TERM` unset or unknown to terminfo the height read 0, and every result paged (w5/586)."""
    ledger = tmp_path / "main.bean"
    lines = ["2026-01-01 open Assets:Cash USD", "2026-01-01 open Expenses:Food USD"]
    for day in range(1, 13):
        lines.append(f'2026-02-{day:02d} * "lunch {day}"\n  Expenses:Food  {day}.00 USD\n  Assets:Cash')
    ledger.write_text("\n".join(lines) + "\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        HOME=str(tmp_path / "home"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        PAGER="less",
        LINES="6",
        COLUMNS="80",
    )
    env.pop("TERM", None)
    if term is not None:
        env["TERM"] = term
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover - replaced by exec in the child
        os.chdir(tmp_path)
        os.execve(sys.executable, [sys.executable, "-m", "cli.main", "-f", "main.bean", "query"], env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 6, 80, 0, 0))
    script = [b"SELECT date, account, position WHERE account ~ 'Food'\r", b".exit\r"]
    emitted = b""
    prompts = 0
    deadline = time.time() + 60
    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if ready:
                try:
                    emitted += os.read(fd, 65536)
                except OSError:
                    pass
            if emitted.count(b"beanquery>") > prompts and script:
                prompts = emitted.count(b"beanquery>")
                os.write(fd, script.pop(0))
            finished, status = os.waitpid(pid, os.WNOHANG)
            if finished:
                break
            if time.time() > deadline:
                os.kill(pid, 9)
                os.waitpid(pid, 0)
                raise AssertionError(f"the session never ended; last output: {emitted[-400:]!r}")
    finally:
        os.close(fd)

    assert os.waitstatus_to_exitcode(status) == 0, emitted[-400:]
    screen = emitted.decode("utf-8", "replace")
    # Every row printed straight to the terminal, the last as well as the first.
    assert "2026-02-01" in screen and "2026-02-12" in screen, screen[-600:]
    assert "still running" not in screen and "ResourceWarning" not in screen
