"""`bea ask`'s prompt history is owner-only and can be turned off (w5/455).

prompt_toolkit created `ask_history` at `0666 & ~umask` in a default-mode
config directory, so every question — finances, pasted account numbers —
was readable by any local user, with no way to keep it off disk.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from pathlib import Path

import pytest
from prompt_toolkit.history import FileHistory, InMemoryHistory

from cli.ask import repl
from cli.config import history_path

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")


@pytest.fixture
def permissive_umask() -> Iterator[None]:
    previous = os.umask(0o022)
    try:
        yield
    finally:
        os.umask(previous)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


@pytest.mark.usefixtures("permissive_umask")
def test_a_fresh_history_is_private(bea_config_dir: Path) -> None:
    history = repl._history()
    assert isinstance(history, FileHistory)
    history.store_string("my card number is 4111 1111 1111 1111")
    assert _mode(history_path()) == 0o600
    assert _mode(history_path().parent) == 0o700


@pytest.mark.usefixtures("permissive_umask")
def test_an_existing_world_readable_history_is_tightened(bea_config_dir: Path) -> None:
    history_path().parent.mkdir(parents=True, exist_ok=True)
    history_path().write_text("\n# old\n+question\n")
    history_path().chmod(0o644)
    repl._history()
    assert _mode(history_path()) == 0o600
    assert "+question" in history_path().read_text()  # Kept, not truncated.


def test_the_opt_out_writes_no_history(bea_config_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEA_NO_ASK_HISTORY", "1")
    history = repl._history()
    assert isinstance(history, InMemoryHistory)
    history.store_string("kept in memory")
    assert not history_path().exists()
