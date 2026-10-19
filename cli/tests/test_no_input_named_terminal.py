"""A `--from` path naming a terminal is refused at once when unattended (w5/737).

`--from -` on a terminal refuses under `--no-input`/`--json`/`CI` (w5/210),
but `--from /dev/stdin` (or `/dev/fd/0`, or `/dev/tty`) opened the terminal
and waited for a human instead. A named path that opens to a terminal is now
refused with the same message; pipes, regular files, and an interactive run
that types the rows still read.
"""

from __future__ import annotations

import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.test_no_input_terminal_stdin import _env, _on_a_terminal

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX device paths and a pseudo-terminal")

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2020-01-01 open Assets:Bank USD\n"
ROWS = '[{"date":"2020-02-01","narration":"Lunch","postings":[{"account":"Assets:Bank","amount":"0 USD"}]}]'
REFUSAL = "Transactions are required with --no-input."


@pytest.mark.parametrize(
    ("args", "env"),
    [
        (["--json", "--file", "main.bean", "add", "transactions", "--from", "/dev/stdin"], {}),
        (["--no-input", "--file", "main.bean", "add", "transactions", "--from", "/dev/stdin"], {}),
        (["--file", "main.bean", "add", "transactions", "--from", "/dev/fd/0"], {"CI": "1"}),
    ],
)
def test_a_named_terminal_is_refused_at_once_when_unattended(
    tmp_path: Path, args: list[str], env: dict[str, str]
) -> None:
    file = tmp_path / "main.bean"
    file.write_text(LEDGER, encoding="utf-8")

    start = time.monotonic()
    code, screen = _on_a_terminal(tmp_path, args, env=env)
    elapsed = time.monotonic() - start

    assert code == 2, screen
    assert REFUSAL in screen
    assert elapsed < 10, f"waited {elapsed:.1f}s for a human"
    assert file.read_text(encoding="utf-8") == LEDGER


def test_dev_tty_is_refused_without_stdin(tmp_path: Path) -> None:
    file = tmp_path / "main.bean"
    file.write_text(LEDGER, encoding="utf-8")

    pid, master = pty.fork()
    if pid == 0:  # Child: the pty is the controlling terminal; stdin is nothing.
        try:
            null = os.open(os.devnull, os.O_RDONLY)
            os.dup2(null, 0)
            os.close(null)
            os.execve(
                sys.executable,
                [
                    sys.executable,
                    "-m",
                    "cli.main",
                    "--file",
                    str(file),
                    "add",
                    "transactions",
                    "--from",
                    "/dev/tty",
                ],
                _env(tmp_path, {"CI": "1"}),
            )
        finally:
            os._exit(127)
    screen = b""
    deadline = time.monotonic() + 15
    raw: int | None = None
    eof = False
    try:
        while time.monotonic() < deadline:
            exited, status = os.waitpid(pid, os.WNOHANG)
            if exited:
                raw = status
                break
            if not eof and select.select([master], [], [], 0.1)[0]:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    chunk = b""
                if not chunk:
                    eof = True
                screen += chunk
        if raw is None:
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
            raise AssertionError(f"bea waited on /dev/tty: {screen!r}")
    finally:
        os.close(master)

    assert os.waitstatus_to_exitcode(raw) == 2, screen
    assert REFUSAL in screen.decode().replace("\r\n", "\n")
    assert file.read_text(encoding="utf-8") == LEDGER


def test_piped_dev_stdin_is_still_read(tmp_path: Path) -> None:
    file = tmp_path / "main.bean"
    file.write_text(LEDGER, encoding="utf-8")

    added = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", "main.bean", "add", "transactions", "--from", "/dev/stdin"],
        cwd=tmp_path,
        env=_env(tmp_path),
        input=ROWS,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert added.returncode == 0, added.stderr
    assert "Added 1 transaction" in added.stdout
    assert '2020-02-01 * "Lunch"' in file.read_text(encoding="utf-8")


def test_an_interactive_run_may_still_type_a_named_terminal(tmp_path: Path) -> None:
    file = tmp_path / "main.bean"
    file.write_text(LEDGER, encoding="utf-8")

    code, screen = _on_a_terminal(
        tmp_path,
        ["--file", "main.bean", "add", "transactions", "--from", "/dev/stdin"],
        typed=ROWS.encode() + b"\n\x04",
    )

    assert code == 0, screen
    assert "Added 1 transaction" in screen
    assert '2020-02-01 * "Lunch"' in file.read_text(encoding="utf-8")
