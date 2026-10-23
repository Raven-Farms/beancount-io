"""Human confirmations show a control byte in a path inertly, and init's hint still replays (w5/887).

`output.success` printed its message raw, so a path holding `ESC [ 2 J` erased
the terminal, and init's piped `Next:` line lost the sequence to Click's ANSI
stripping and named a directory that does not exist.
"""

from __future__ import annotations

import json
import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ESC = "\x1b"
EVIL = f"books{ESC}[2J"


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=_env(tmp_path),
        cwd=tmp_path,
        input="",
        capture_output=True,
        text=True,
        timeout=120,
    )


def _init(tmp_path: Path, directory: str = EVIL) -> subprocess.CompletedProcess[str]:
    return _bea(tmp_path, "init", str(tmp_path / directory), "--currency", "USD", "--date", "2024-01-01")


def test_init_prints_the_path_inertly_and_its_hint_replays(tmp_path: Path) -> None:
    created = _init(tmp_path)

    assert created.returncode == 0, created.stderr
    assert ESC not in created.stdout
    assert "books\\x1b[2J" in created.stdout
    (hint,) = [line[len("Next: ") :] for line in created.stdout.splitlines() if line.startswith("Next: ")]
    replay = subprocess.run(["sh", "-c", hint], env=_env(tmp_path), cwd=tmp_path, capture_output=True, text=True)
    assert replay.returncode == 0, (hint, replay.stderr)
    assert (tmp_path / EVIL / "main.bean").exists()


@pytest.mark.parametrize("name", ["plain", "with space", "100%\\n"])
def test_an_ordinary_hint_is_unchanged_by_the_control_handling(tmp_path: Path, name: str) -> None:
    created = _init(tmp_path, name)

    assert created.returncode == 0, created.stderr
    (hint,) = [line[len("Next: ") :] for line in created.stdout.splitlines() if line.startswith("Next: ")]
    assert "printf" not in hint
    replay = subprocess.run(["sh", "-c", hint], env=_env(tmp_path), cwd=tmp_path, capture_output=True, text=True)
    assert replay.returncode == 0, (hint, replay.stderr)


def test_the_write_confirmations_are_inert_and_json_keeps_the_exact_path(tmp_path: Path) -> None:
    ledger = tmp_path / f"main{ESC}[2J.bean"
    ledger.write_text("2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Uncategorized USD\n")
    (tmp_path / "bank.csv").write_text("Date,Description,Amount\n2024-02-02,Payment,-2.00\n")

    note = _bea(
        tmp_path,
        "-f",
        str(ledger),
        "add",
        "note",
        "--account",
        "Assets:Cash",
        "--date",
        "2024-02-01",
        "--comment",
        "hi",
    )
    imported = _bea(
        tmp_path, "-f", str(ledger), "import", "bank.csv", "--csv", "date=Date,narration=Description,amount=Amount",
        "--account", "Assets:Cash", "--apply",
    )  # fmt: skip
    for result in (note, imported):
        assert result.returncode == 0, result.stderr
        assert ESC not in result.stdout
        assert "main\\x1b[2J.bean" in result.stdout

    structured = _bea(
        tmp_path,
        "--json",
        "-f",
        str(ledger),
        "add",
        "note",
        "--account",
        "Assets:Cash",
        "--date",
        "2024-02-03",
        "--comment",
        "j",
    )
    assert json.loads(structured.stdout)["target"]["file"] == str(ledger)


def test_a_terminal_never_receives_the_erase_sequence(tmp_path: Path) -> None:
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover - replaced by exec in the child
        os.chdir(tmp_path)
        argv = [
            sys.executable,
            "-m",
            "cli.main",
            "--no-input",
            "init",
            EVIL,
            "--currency",
            "USD",
            "--date",
            "2024-01-01",
        ]
        os.execve(sys.executable, argv, _env(tmp_path))
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
            assert time.time() < deadline, screen
    finally:
        os.close(fd)

    assert os.waitstatus_to_exitcode(status) == 0, screen
    assert b"\x1b" not in screen
    assert b"books\\x1b[2J" in screen
