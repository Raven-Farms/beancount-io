"""Ctrl-C inside the spinner startup cancels the turn, not the session (w5/734).

`status.start()` sat outside the `try` whose `except KeyboardInterrupt`
cancels the turn, so a Ctrl-C landing there escaped the REPL and ended the
process with exit 130, losing the conversation. The whole turn setup sits
inside now, and the turn's write record resets when the turn begins — so a
turn cancelled before its run never names the previous turn's writes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

from cli.ask import repl
from cli.ask.agent import BqlDeps


class _Session:
    """A prompt that replays a script: a string is typed, an exception is pressed."""

    def __init__(self, script: list[object]) -> None:
        self._script = list(script)

    def prompt(self, **kwargs: object) -> str:
        if not self._script:
            raise EOFError
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return str(item)


class _Agent:
    """An agent whose turns are scripted: an exception, an answer, or a write."""

    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.histories: list[list[Any]] = []

    def run_sync(self, prompt: str, *, deps: Any, message_history: list[Any], **kwargs: object) -> Any:
        self.histories.append(list(message_history))
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        if outcome == "WRITE":
            deps.writes.append((1, str(deps.file)))
            outcome = "one"
        return type("R", (), {"output": str(outcome), "all_messages": lambda self: [prompt, outcome]})()


def _boom_on_start(number: int, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the `number`-th spinner startup raise Ctrl-C, counting from 1."""
    real_status = Console.status
    calls = 0

    def flaky_status(self: Console, *args: object, **kwargs: object) -> Any:
        nonlocal calls
        calls += 1
        handle = real_status(self, *args, **kwargs)
        if calls == number:
            handle.start = lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt())  # type: ignore[method-assign]
        return handle

    monkeypatch.setattr(Console, "status", flaky_status)


def _run(script: list[object], outcomes: list[object], ledger: Path, monkeypatch: pytest.MonkeyPatch) -> _Agent:
    agent = _Agent(outcomes)
    monkeypatch.setattr(repl, "_make_session", lambda hint, key_bindings=None: _Session(script))
    repl.run_repl(agent, BqlDeps(file=ledger))  # type: ignore[arg-type]
    return agent


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text('option "operating_currency" "USD"\n', encoding="utf-8")
    return path


def test_ctrl_c_in_the_spinner_startup_cancels_only_that_turn(
    ledger: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _boom_on_start(2, monkeypatch)
    agent = _run(["first", "second", "third"], ["WRITE", "three"], ledger, monkeypatch)

    assert len(agent.histories) == 2, "the cancelled turn never ran"
    assert agent.histories[1] == ["first", "one"], "the cancelled turn left no trace"
    out = capsys.readouterr().out
    assert "(cancelled)" in out
    assert "already written" not in out, "the previous turn's write was named again"
    assert "three" in out, "the session answered the question after the cancel"
    assert "Goodbye." in out


def test_ctrl_c_in_the_first_spinner_startup_keeps_the_session(
    ledger: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _boom_on_start(1, monkeypatch)
    agent = _run(["first", "second"], ["two"], ledger, monkeypatch)

    assert len(agent.histories) == 1
    assert agent.histories[0] == []
    out = capsys.readouterr().out
    assert "(cancelled)" in out
    assert "two" in out
    assert "Goodbye." in out
