"""`bea ask` keeps its history only in a regular file of its own (w5/810).

A symbolic link at `<config>/ask_history` was followed: its target outside
the config directory was chmodded to 0600 and every question appended to it.
A FIFO there blocked the open, so the session printed its banner and never
showed a prompt. Both now fall back to in-memory history with a note.
"""

from __future__ import annotations

import os
import stat
import threading
from pathlib import Path

import pytest
from prompt_toolkit.history import FileHistory, History, InMemoryHistory

from cli.ask import repl
from cli.config import history_path

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX links and FIFOs")


def _history_within(seconds: float) -> History:
    """`repl._history()`, failing instead of hanging when the open blocks."""
    found: list[History] = []
    worker = threading.Thread(target=lambda: found.append(repl._history()), daemon=True)
    worker.start()
    worker.join(seconds)
    assert found, "opening the history blocked"
    return found[0]


def test_a_linked_history_is_not_followed(
    bea_config_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    precious = tmp_path / "precious.txt"
    precious.write_text("precious\n")
    precious.chmod(0o644)
    history_path().parent.mkdir(parents=True, exist_ok=True)
    history_path().symlink_to(precious)

    history = _history_within(10)
    history.store_string("my card number is 4111 1111 1111 1111")

    assert isinstance(history, InMemoryHistory)
    assert stat.S_IMODE(precious.stat().st_mode) == 0o644
    assert precious.read_text() == "precious\n"
    assert history_path().is_symlink()
    assert "kept in memory only" in " ".join(capsys.readouterr().err.split())


def test_a_fifo_history_does_not_block_the_prompt(bea_config_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    history_path().parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(history_path())

    history = _history_within(10)

    assert isinstance(history, InMemoryHistory)
    assert stat.S_ISFIFO(os.lstat(history_path()).st_mode)
    assert "kept in memory only" in " ".join(capsys.readouterr().err.split())


def test_a_regular_history_is_still_kept(bea_config_dir: Path) -> None:
    history = _history_within(10)

    assert isinstance(history, FileHistory)
    history.store_string("kept on disk")
    assert "+kept on disk" in history_path().read_text()
    assert stat.S_IMODE(history_path().stat().st_mode) == 0o600
