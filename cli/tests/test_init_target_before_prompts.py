"""`bea init` refuses a target it cannot create before asking anything (w5/813).

On a terminal, a file where the ledger's directory goes, a read-only parent,
or a dangling-link parent was refused only after all three questions had
been answered. And `--currency 12` was refused as `Invalid value: …` without
naming the option.
"""

from __future__ import annotations

import os
import pty
import select
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX terminal")


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _on_a_terminal(tmp_path: Path, target: Path) -> tuple[int, str]:
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover - replaced by exec in the child
        os.chdir(tmp_path)
        os.execve(sys.executable, [sys.executable, "-m", "cli.main", "init", str(target)], _env(tmp_path))
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
            assert time.time() < deadline, f"init waited at a question first: {screen!r}"
    finally:
        os.close(fd)
    return os.waitstatus_to_exitcode(status), " ".join(screen.decode("utf-8", "replace").split())


def _a_file(tmp_path: Path) -> tuple[Path, int, str]:
    (tmp_path / "i4").mkdir()
    (tmp_path / "i4" / "notes").write_text("")
    notes = tmp_path / "i4" / "notes"
    return notes, 2, f"Cannot create a ledger in {notes}: {notes} is a file, not a directory."


def _a_read_only_parent(tmp_path: Path) -> tuple[Path, int, str]:
    (tmp_path / "ro").mkdir()
    (tmp_path / "ro").chmod(0o555)
    books = tmp_path / "ro" / "books"
    return books, 3, f"Cannot create {books}: the directory {tmp_path / 'ro'} is not writable."


def _a_dangling_link(tmp_path: Path) -> tuple[Path, int, str]:
    (tmp_path / "dl").symlink_to(tmp_path / "nowhere")
    books = tmp_path / "dl" / "books"
    return books, 2, f"Cannot create a ledger in {books}: {tmp_path / 'dl'} is a broken symbolic link to"


TARGETS: dict[str, Callable[[Path], tuple[Path, int, str]]] = {
    "file": _a_file,
    "read-only-parent": _a_read_only_parent,
    "dangling-link": _a_dangling_link,
}


@pytest.mark.parametrize("kind", sorted(TARGETS))
def test_an_uncreatable_target_is_refused_before_the_first_question(tmp_path: Path, kind: str) -> None:
    if kind == "read-only-parent" and hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root writes through a read-only directory")
    target, code, message = TARGETS[kind](tmp_path)
    try:
        status, shown = _on_a_terminal(tmp_path, target)
    finally:
        if (tmp_path / "ro").exists():
            (tmp_path / "ro").chmod(0o755)

    assert status == code, shown
    assert message in shown, shown
    assert "Nothing was written" in shown
    assert "Operating currency" not in shown


def test_a_bad_currency_names_the_option(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "init", str(tmp_path / "pb"), "--currency", "12"],
        cwd=tmp_path,
        env=_env(tmp_path),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 2, result.stderr
    message = " ".join(result.stderr.split())
    assert "--currency '12': Invalid operating currency: '12'. Use a symbol such as USD or EUR." in message
    assert "Invalid value:" not in message
    assert not (tmp_path / "pb").exists()
