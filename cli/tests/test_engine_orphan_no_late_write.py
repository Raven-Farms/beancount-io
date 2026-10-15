"""A write whose frontend was SIGKILLed never lands later (w5/300).

The write helper runs in its own session, so `kill -9` on `bea` reached only
the frontend: the orphaned engine finished validating and committed seconds
later, and a caller that saw the kill and retried recorded the entry twice.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from tests.test_into_glob_create import ROOT, _env

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX re-parenting")

LEDGER = 'option "operating_currency" "USD"\nplugin "orphan_barrier"\n2024-01-01 open Assets:Bank USD\n'


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_a_killed_frontend_leaves_the_ledger_as_it_was(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    ledger = books / "main.bean"
    ledger.write_text(LEDGER)
    ready = tmp_path / "ready.json"
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    # Pauses only the staged candidate's validation, long enough to kill the
    # frontend, then lets the helper go on as an orphan would.
    (plugins / "orphan_barrier.py").write_text(
        textwrap.dedent(
            f"""\
            import json, os, time
            from pathlib import Path

            __plugins__ = ("pause",)

            def pause(entries, options):
                candidate = Path(options["filename"])
                if candidate.name.startswith(".bea-"):
                    ready = Path({str(ready)!r})
                    pending = ready.with_suffix(".pending")
                    pending.write_text(json.dumps({{"pid": os.getpid(), "candidate": str(candidate)}}))
                    pending.replace(ready)
                    time.sleep(3)
                return entries, []
            """
        )
    )
    env = _env(tmp_path)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(plugins)])
    command = [sys.executable, "-m", "cli.main", "--no-input", "-f", str(ledger)]
    command += ["add", "note", "--date", "2026-01-05", "-a", "Assets:Bank", "-m", "late"]
    frontend = subprocess.Popen(
        command, env=env, cwd=books, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        deadline = time.monotonic() + 60
        while not ready.exists():
            assert frontend.poll() is None, "the write finished before the barrier"
            assert time.monotonic() < deadline, "the helper never reached validation"
            time.sleep(0.05)
        staged = json.loads(ready.read_text())
        frontend.send_signal(signal.SIGKILL)
        frontend.wait(timeout=10)
    finally:
        if frontend.poll() is None:
            frontend.kill()

    helper = staged["pid"]
    deadline = time.monotonic() + 15
    while _alive(helper) and time.monotonic() < deadline:
        time.sleep(0.1)
    if _alive(helper):
        os.kill(helper, signal.SIGKILL)
        pytest.fail("the orphaned helper outlived its frontend")
    # Past the barrier's sleep: a helper that carried on would have committed.
    time.sleep(1)
    assert ledger.read_text() == LEDGER
    assert not Path(staged["candidate"]).exists()
    assert not [path.name for path in books.iterdir() if path.name.startswith(".bea-")]
