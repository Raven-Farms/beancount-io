"""Questions are asked on stderr, so a redirected stdout cannot hide them (w5/163).

`bea init books > log` typed in a terminal showed nothing and waited: the
"Operating currency [USD]:" question had been written into the redirect, and
the captured stdout held the prompts glued to the result. The same held for
the confirmation that guards `cloud ledger delete`.
"""

from __future__ import annotations

import os
import pty
import select
import subprocess
import sys
import termios
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()

QUESTIONS = ["Operating currency [USD]: ", "Earliest date you will record", "Checking opening balance on 2026-01-01"]
# What to await on the terminal, in order, and what to type once it shows.
SCRIPT = list(zip(QUESTIONS, ["EUR", "2026-01-01", "5"], strict=True))


@dataclass
class Run:
    exit_code: int
    terminal: str
    stdout: str
    stderr: str
    asked_before_typing: bool


def _init_on_a_terminal(
    tmp_path: Path, args: list[str], *, stdout: str, stderr: str, script: list[tuple[str, str]] = SCRIPT
) -> Run:
    """Run `bea init` with stdin on a PTY and each output on the PTY or a pipe, answering as asked."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        HOME=str(tmp_path),
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    master, slave = pty.openpty()
    attrs = termios.tcgetattr(slave)
    attrs[3] &= ~termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "cli.main", "init", *args],
            cwd=tmp_path,
            env=env,
            stdin=slave,
            stdout=slave if stdout == "terminal" else subprocess.PIPE,
            stderr=slave if stderr == "terminal" else subprocess.PIPE,
            start_new_session=True,
        )
    finally:
        os.close(slave)
    screen = b""
    answered = 0
    matched = 0
    deadline = time.monotonic() + 60
    try:
        while process.poll() is None and time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    screen += os.read(master, 4096)
                except OSError:  # Linux: EIO once the child has closed the terminal.
                    break
            if answered < len(script):
                marker, answer = script[answered]
                found = screen.find(marker.encode(), matched)
                if found >= 0:
                    matched = found + len(marker)
                    os.write(master, (answer + "\n").encode())
                    answered += 1
        # Linux closes the terminal (EIO) while the child is still exiting, before
        # it can be reaped, so only the wait decides whether the run ended.
        try:
            out, err = process.communicate(timeout=max(deadline - time.monotonic(), 10))
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=10)
            raise AssertionError(f"bea init {args} waited with nothing asked on the terminal: {screen!r}") from None
        while select.select([master], [], [], 0.1)[0]:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            screen += chunk
    finally:
        os.close(master)
    return Run(
        process.returncode,
        screen.decode().replace("\r\n", "\n"),
        (out or b"").decode(),
        (err or b"").decode(),
        answered > 0,
    )


@pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pseudo-terminal")
class TestInitOnATerminal:
    def test_a_redirected_stdout_holds_only_the_result(self, tmp_path: Path) -> None:
        run = _init_on_a_terminal(tmp_path, ["b1"], stdout="pipe", stderr="terminal")

        assert run.exit_code == 0, run.terminal
        assert run.asked_before_typing
        for question in QUESTIONS:
            assert question in run.terminal
            assert question not in run.stdout
        assert run.stdout.startswith(f"Created {tmp_path / 'b1/main.bean'} with ")
        assert "EUR" in (tmp_path / "b1/main.bean").read_text()

    def test_a_rejected_answer_is_explained_on_the_terminal(self, tmp_path: Path) -> None:
        """The re-prompt error belongs with the question, not in the captured result."""
        script = [(QUESTIONS[0], "US D"), ("Invalid operating currency: 'US D'", "EUR"), *SCRIPT[1:]]

        run = _init_on_a_terminal(tmp_path, ["b1"], stdout="pipe", stderr="terminal", script=script)

        assert run.exit_code == 0, run.terminal
        assert run.terminal.count(QUESTIONS[0]) == 2
        assert run.stdout.startswith("Created ")

    def test_both_outputs_redirected_refuses_instead_of_waiting(self, tmp_path: Path) -> None:
        run = _init_on_a_terminal(tmp_path, ["b1"], stdout="pipe", stderr="pipe")

        assert run.exit_code == 2
        assert run.stdout == ""
        assert "--currency" in run.stderr
        assert run.terminal == ""
        assert not (tmp_path / "b1").exists()

    def test_both_outputs_redirected_takes_the_defaults_for_the_rest(self, tmp_path: Path) -> None:
        """With the currency named, the remaining questions default as under `--no-input`."""
        run = _init_on_a_terminal(tmp_path, ["b1", "--currency", "EUR"], stdout="pipe", stderr="pipe")

        assert run.exit_code == 0, run.stderr
        assert run.stdout.startswith("Created ")
        assert run.terminal == ""

    def test_control_everything_on_the_terminal_still_asks(self, tmp_path: Path) -> None:
        run = _init_on_a_terminal(tmp_path, ["b1"], stdout="terminal", stderr="terminal")

        assert run.exit_code == 0, run.terminal
        assert run.asked_before_typing
        for question in QUESTIONS:
            assert question in run.terminal
        assert "Created " in run.terminal


class TestConfirmation:
    def test_the_delete_question_is_asked_on_stderr(self, logged_in: None, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cli.context._stdin_is_a_terminal", lambda: True)
        monkeypatch.setattr("cli.context._stderr_is_a_terminal", lambda: True)

        result = runner.invoke(app, ["cloud", "ledger", "delete", "alice/books"], input="n\n")

        assert result.exit_code == 0, result.output
        assert "Permanently delete ledger 'alice/books'? [y/N]: " in result.stderr
        assert result.stdout == "Cancelled.\n"

    def test_an_unseen_delete_question_is_refused(self, logged_in: None, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cli.context._stdin_is_a_terminal", lambda: True)
        monkeypatch.setattr("cli.context._stderr_is_a_terminal", lambda: False)

        result = runner.invoke(app, ["cloud", "ledger", "delete", "alice/books"], input="y\n")

        assert result.exit_code == 2
        assert result.stdout == ""
        assert "--yes" in result.stderr
