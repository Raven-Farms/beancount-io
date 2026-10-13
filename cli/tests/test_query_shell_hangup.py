"""A closed terminal ends the query shell, and SIGTERM always can (w5/234).

The engine installs Python-level handlers for SIGTERM and SIGHUP so a stopped
write unwinds, and the interactive shells kept them. A Python handler only runs
when the interpreter regains control, and with text on the line the line editor
never gives it back once the terminal is gone: it reads end-of-file, finds a
non-empty buffer and reads again. Closing the window on a half-typed query left
the helper at full CPU, deaf to SIGTERM, until something sent SIGKILL — the
frontend after its grace period, or nobody once the frontend was gone.

The shells stage nothing, so both signals keep their default disposition there
and the kernel ends the process whatever the line editor is doing.
"""

from __future__ import annotations

import fcntl
import os
import pty
import select
import signal
import subprocess
import sys
import termios
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX terminals and signals")

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Cafe" "Coffee"
  Expenses:Food  4.00 USD
  Assets:Cash
"""
PROMPT = "beanquery> "
HALF_TYPED = "SELECT cou"
#: Well inside the five seconds after which the frontend kills a deaf child.
PROMPTLY = 3.0


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    books = tmp_path / "books-w5-234"
    books.mkdir()
    path = books / "main.bean"
    path.write_text(LEDGER)
    return path


def _take_terminal() -> None:
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)


@contextmanager
def _session(
    home: Path, command: list[str], *, controlling: bool, typed: str
) -> Iterator[tuple[subprocess.Popen[bytes], Callable[[], None]]]:
    """`command` at its prompt on a PTY, with `typed` on the line; yields it and a way to close the terminal.

    `controlling` makes the PTY the session's controlling terminal, so closing
    the master hangs the session up the way closing a window does. Without it
    the close is only end-of-file on the streams.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        HOME=str(home),  # The shell keeps its history under $HOME/.config/beanquery.
        BEA_CONFIG_DIR=str(home / "config"),
        BEA_ENGINE_DIR=str(home / "engine"),
        BEA_NO_UPDATE_NOTIFIER="1",
        XDG_CACHE_HOME=str(home / "cache"),
        XDG_DATA_HOME=str(home / "data"),
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    master, slave = pty.openpty()
    try:
        process = subprocess.Popen(
            command,
            cwd=home,
            env=env,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
            preexec_fn=_take_terminal if controlling else None,
        )
    finally:
        os.close(slave)
    open_fds = [master]

    def close_terminal() -> None:
        while open_fds:
            os.close(open_fds.pop())

    try:
        _read_until(master, PROMPT)
        if typed:
            os.write(master, typed.encode())
            # Echoed means the line editor holds it, and the terminal is drained.
            _read_until(master, typed)
        yield process, close_terminal
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
        close_terminal()


def _read_until(master: int, expected: str) -> None:
    screen = ""
    deadline = time.monotonic() + 60
    while expected not in screen and time.monotonic() < deadline:
        if select.select([master], [], [], 0.1)[0]:
            try:
                chunk = os.read(master, 8192)
            except OSError:
                break
            if not chunk:
                break
            screen += chunk.decode("utf-8", "replace")
    assert expected in screen, f"expected {expected!r}, got {screen[-2000:]!r}"


def _naming(ledger: Path) -> list[str]:
    """Live processes whose command line names the ledger."""
    listing = subprocess.run(
        ["ps", "-axo", "pid=,stat=,command="], capture_output=True, text=True, check=True, timeout=30
    ).stdout
    return [
        line.strip() for line in listing.splitlines() if str(ledger) in line and not line.split()[1].startswith("Z")
    ]


def _frontend(mode: str, ledger: Path) -> list[str]:
    bea = str(ROOT / ".venv/bin/bea")
    return [bea, "query", "--source", str(ledger)] if mode == "source" else [bea, "-f", str(ledger), "query"]


def _helper(mode: str, ledger: Path) -> list[str]:
    """The helper as the frontend launches it, with nothing above it to kill it."""
    python = [sys.executable, "-P", "-m", "bea_engine"]
    return (
        [*python, "source-shell", "--", str(ledger)] if mode == "source" else [*python, "shell", "--file", str(ledger)]
    )


@pytest.mark.parametrize("mode", ["file", "source"])
@pytest.mark.parametrize("typed", [HALF_TYPED, ""], ids=["half-typed", "empty-prompt"])
def test_closing_the_terminal_leaves_no_process(tmp_path: Path, ledger: Path, mode: str, typed: str) -> None:
    with _session(tmp_path, _frontend(mode, ledger), controlling=True, typed=typed) as (process, close_terminal):
        assert len(_naming(ledger)) == 2, "the frontend and its engine child"

        close_terminal()

        deadline = time.monotonic() + PROMPTLY
        while (left := _naming(ledger)) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert left == []
        assert process.wait(timeout=10) == -signal.SIGHUP


@pytest.mark.parametrize("mode", ["file", "source"])
def test_a_hangup_ends_the_helper_on_its_own(tmp_path: Path, ledger: Path, mode: str) -> None:
    """The orphan: no frontend is left to kill a helper that will not listen.

    The old handler lost a race here rather than every time, so the status is
    what is pinned: the kernel ended the process, no interpreter involved.
    """
    with _session(tmp_path, _helper(mode, ledger), controlling=True, typed=HALF_TYPED) as (process, close_terminal):
        close_terminal()

        assert process.wait(timeout=10) == -signal.SIGHUP


@pytest.mark.parametrize("mode", ["file", "source"])
def test_sigterm_ends_a_helper_reading_a_dead_terminal(tmp_path: Path, ledger: Path, mode: str) -> None:
    """Not the session's terminal, so its closing sends no signal and the line editor is left reading end-of-file."""
    with _session(tmp_path, _helper(mode, ledger), controlling=False, typed=HALF_TYPED) as (process, close_terminal):
        close_terminal()
        time.sleep(0.5)
        if process.poll() is not None:
            pytest.skip("This line editor takes end-of-file on a half-typed line as the end of input.")

        process.send_signal(signal.SIGTERM)

        assert process.wait(timeout=10) == -signal.SIGTERM


@pytest.mark.parametrize("mode", ["file", "source"])
@pytest.mark.parametrize("typed", [HALF_TYPED, ""], ids=["half-typed", "empty-prompt"])
def test_sigterm_ends_a_live_session(tmp_path: Path, ledger: Path, mode: str, typed: str) -> None:
    """The control: a terminal that still answers always let the signal through."""
    with _session(tmp_path, _helper(mode, ledger), controlling=True, typed=typed) as (process, _):
        process.send_signal(signal.SIGTERM)

        assert process.wait(timeout=10) in (-signal.SIGTERM, 128 + signal.SIGTERM)
