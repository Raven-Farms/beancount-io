"""`bea --version | true` exits 141 without a message, like any command body (w5/122).

The root's eager options — `--version`, `--help`/`-h`, `--show-completion` —
print and exit from inside argument parsing, before the group's `invoke` guard
that gave command bodies the documented closed-pipe exit (w3/378). A reader
that had already gone got `Error: [Errno 32] Broken pipe`, CPython's
"Exception ignored on flushing sys.stdout" and exit 120, a code outside the
exit table.

Their output is far smaller than a pipe buffer, so piping into `head` would
race the reader's exit. Each case instead hands `bea` a pipe whose read end is
closed before the child starts: the very first write is the one that fails.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

EAGER = [
    pytest.param(("--version",), id="version"),
    pytest.param(("--help",), id="help"),
    pytest.param(("-h",), id="short-help"),
    pytest.param(("--shell", "zsh", "--show-completion"), id="show-completion"),
    # Buffered rather than flushed by the callback, so this one only failed at
    # interpreter shutdown: no `Error:` line, still exit 120.
    pytest.param(("--json", "--version"), id="json-version"),
]


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _run(tmp_path: Path, args: tuple[str, ...], *, stdout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=_env(tmp_path),
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize("args", EAGER)
def test_eager_option_exits_141_silently_when_the_reader_has_gone(tmp_path: Path, args: tuple[str, ...]) -> None:
    read_end, write_end = os.pipe()
    os.close(read_end)  # Nobody will ever read: the child's first write gets EPIPE.
    try:
        done = _run(tmp_path, args, stdout=write_end)
    finally:
        os.close(write_end)
    assert done.returncode == 141, f"expected the documented closed-pipe status; stderr={done.stderr!r}"
    assert done.stderr == "", "a closed downstream pipe has nowhere to report to and must stay silent"


@pytest.mark.parametrize("args", EAGER)
def test_eager_option_still_answers_a_reader_that_stays(tmp_path: Path, args: tuple[str, ...]) -> None:
    """The control: settling stdout must not cost a complete run its output or its 0."""
    done = _run(tmp_path, args, stdout=subprocess.PIPE)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip()
    assert done.stderr == ""


def test_parse_failure_keeps_its_own_status_when_the_reader_has_gone(tmp_path: Path) -> None:
    """Only a failed write becomes 141 — a usage error writes to stderr and stays 2."""
    read_end, write_end = os.pipe()
    os.close(read_end)
    try:
        done = _run(tmp_path, ("--no-such-option",), stdout=write_end)
    finally:
        os.close(write_end)
    assert done.returncode == 2
    assert "No such option" in done.stderr
