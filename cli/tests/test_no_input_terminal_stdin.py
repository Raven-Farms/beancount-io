"""An unattended run never reads its input from a terminal (w5/210).

`bea --no-input format`, `add transactions --from -` and `treeify` read stdin
even when it was a terminal: they printed nothing and waited for Ctrl-D, so a
CI job with an allocated TTY hung until its timeout. `bea query` already
refused with exit 2.
"""

from __future__ import annotations

import os
import pty
import select
import subprocess
import sys
import termios
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = "2020-01-01 open Assets:Bank USD\n"
TYPED = "2021-03-04 open Assets:Typed USD\n"
FORMAT_REFUSAL = "A ledger is required with --no-input."
ADD_REFUSAL = "Transactions are required with --no-input."
TREEIFY_REFUSAL = "Input is required with --no-input."

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pseudo-terminal")


def _env(tmp_path: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        HOME=str(tmp_path),
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    env.update(extra or {})
    return env


def _ledger(tmp_path: Path) -> Path:
    file = tmp_path / "main.bean"
    file.write_text(LEDGER, encoding="utf-8")
    return file


def _on_a_terminal(
    tmp_path: Path, args: list[str], *, env: dict[str, str] | None = None, typed: bytes | None = None
) -> tuple[int, str]:
    """Run `bea` with stdin, stdout and stderr on one PTY; a run that waits fails the test."""
    master, slave = pty.openpty()
    # Without echo the screen holds only what `bea` wrote, not what was typed.
    attrs = termios.tcgetattr(slave)
    attrs[3] &= ~termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "cli.main", *args],
            cwd=tmp_path,
            env=_env(tmp_path, env),
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
        )
    finally:
        os.close(slave)
    screen = b""
    deadline = time.monotonic() + 30
    try:
        if typed is not None:
            os.write(master, typed)
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    chunk = os.read(master, 4096)
                except OSError:  # Linux: EIO once the child has closed the terminal.
                    break
                if not chunk:  # macOS reports the same as end-of-file.
                    break
                screen += chunk
            elif process.poll() is not None:
                break
        # The terminal closes while the child is still exiting, before it can be
        # reaped, so only the wait decides whether the run ended.
        try:
            process.wait(timeout=max(deadline - time.monotonic(), 10))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
            raise AssertionError(f"bea {args} waited on the terminal: {screen!r}") from None
    finally:
        os.close(master)
    return process.returncode, screen.decode().replace("\r\n", "\n")


def _piped(tmp_path: Path, args: list[str], text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path,
        env=_env(tmp_path),
        input=text,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize(
    ("args", "env", "message"),
    [
        (["--no-input", "format"], {}, FORMAT_REFUSAL),
        (["--no-input", "format", "-"], {}, FORMAT_REFUSAL),
        (["format"], {"CI": "true"}, FORMAT_REFUSAL),
        (["--no-input", "add", "transactions", "--from", "-"], {}, ADD_REFUSAL),
        (["--no-input", "--file", "main.bean", "add", "transactions", "--from", "-"], {}, ADD_REFUSAL),
        (["--json", "--file", "main.bean", "add", "transactions", "--from", "-"], {}, ADD_REFUSAL),
        (["add", "transactions", "--from", "-"], {"CI": "1"}, ADD_REFUSAL),
        (["--no-input", "treeify"], {}, TREEIFY_REFUSAL),
        (["--no-input", "treeify", "-o", "tree.txt"], {}, TREEIFY_REFUSAL),
    ],
)
def test_an_unattended_run_refuses_to_read_the_terminal(
    tmp_path: Path, args: list[str], env: dict[str, str], message: str
) -> None:
    file = _ledger(tmp_path)

    code, screen = _on_a_terminal(tmp_path, args, env=env)

    assert code == 2, screen
    assert message in screen
    assert file.read_text(encoding="utf-8") == LEDGER
    assert not (tmp_path / "tree.txt").exists()


def test_the_neighbouring_answers_on_a_terminal_are_unchanged(tmp_path: Path) -> None:
    _ledger(tmp_path)

    code, screen = _on_a_terminal(tmp_path, ["--no-input", "--file", "main.bean", "query"])
    assert code == 2, screen
    assert "A query is required with --no-input. Pass it as an argument or on stdin." in screen

    code, screen = _on_a_terminal(tmp_path, ["--no-input", "format", "main.bean"])
    assert (code, screen) == (0, LEDGER)

    code, screen = _on_a_terminal(tmp_path, ["--json", "format", "--check"])
    assert code == 2, screen
    assert "Name the files to format: reading stdin has nothing to compare or rewrite." in screen


def test_an_interactive_run_may_still_type_the_ledger(tmp_path: Path) -> None:
    # Canonical mode hands the line over at the newline and Ctrl-D ends the input.
    code, screen = _on_a_terminal(tmp_path, ["format"], typed=TYPED.encode() + b"\x04")

    assert (code, screen) == (0, TYPED)


def test_piped_input_is_still_read_under_no_input(tmp_path: Path) -> None:
    file = _ledger(tmp_path)

    for args in (["--no-input", "format"], ["--no-input", "format", "-"]):
        formatted = _piped(tmp_path, args, TYPED)
        assert (formatted.returncode, formatted.stdout) == (0, TYPED), formatted.stderr

    rows = '[{"date":"2020-02-01","narration":"Lunch","postings":[{"account":"Assets:Bank","amount":"0 USD"}]}]'
    added = _piped(tmp_path, ["--no-input", "--file", "main.bean", "add", "transactions", "--from", "-"], rows)
    assert added.returncode == 0, added.stderr
    assert "Added 1 transaction" in added.stdout
    assert '2020-02-01 * "Lunch"' in file.read_text(encoding="utf-8")

    tree = _piped(tmp_path, ["--no-input", "treeify"], "Assets:Bank:A 1\nAssets:Bank:B 2\n")
    assert tree.returncode == 0, tree.stderr
    assert "`-- Bank" in tree.stdout
