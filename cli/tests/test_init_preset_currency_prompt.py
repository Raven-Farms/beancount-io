"""`init --preset` checks the currency against the catalog where it is entered (w5/878).

`BTC` is valid Beancount grammar, so it passed the prompt and `--currency`
checks and was refused only after the date question: the prompt exited
instead of retrying, and the flag still asked for a date first.
"""

from __future__ import annotations

import os
import pty
import select
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(tmp_path: Path, args: list[str], answers: list[str]) -> tuple[int, str]:
    """Run `bea init` on a terminal, sending each answer once its question appears."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover - replaced by exec in the child
        os.chdir(tmp_path)
        os.execve(sys.executable, [sys.executable, "-m", "cli.main", "init", *args], env)
    screen = b""
    sent = 0
    deadline = time.time() + 60
    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if ready:
                try:
                    screen += os.read(fd, 65536)
                except OSError:
                    pass
            # One answer per question: a question is a prompt ending in `]: `.
            if sent < len(answers) and screen.count(b"]: ") > sent:
                os.write(fd, answers[sent].encode() + b"\n")
                sent += 1
            finished, status = os.waitpid(pid, os.WNOHANG)
            if finished:
                break
            assert time.time() < deadline, f"init stalled: {screen!r}"
    finally:
        os.close(fd)
    return os.waitstatus_to_exitcode(status), " ".join(screen.decode("utf-8", "replace").split())


def test_an_unsupported_answer_retries_the_currency_question(tmp_path: Path) -> None:
    code, shown = _run(tmp_path, ["books", "--preset", "personal@1", "--date", "2024-02-01"], ["BTC", "USD"])

    assert code == 0, shown
    assert "Unsupported operating currency 'BTC' for a preset ledger." in shown
    assert shown.count("Operating currency") >= 2
    assert (tmp_path / "books" / "main.bean").exists()


def test_an_unsupported_flag_is_refused_before_any_question(tmp_path: Path) -> None:
    code, shown = _run(tmp_path, ["books", "--preset", "personal@1", "--currency", "BTC"], [])

    assert code == 2, shown
    assert "--currency 'BTC': Unsupported operating currency 'BTC' for a preset ledger." in shown
    assert "Earliest date" not in shown
    assert not (tmp_path / "books").exists()


def test_a_custom_symbol_is_still_fine_without_a_preset(tmp_path: Path) -> None:
    code, shown = _run(tmp_path, ["books", "--currency", "BTC", "--date", "2024-02-01"], [""])

    assert code == 0, shown
    assert (tmp_path / "books" / "main.bean").exists()
