"""Stopping `bea` stops the upstream child it started with inherited streams (w5/208)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from tests.test_into_glob_create import ROOT, _env

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal semantics")


@pytest.fixture
def slow_load(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    """A ledger whose load parks in a plugin, after recording which process is loading it.

    `LOAD_BARRIER_PROGRAM` names the program to park in: `bea check` loads the
    ledger in the helper first and only then starts `bean-check`.
    """
    books = tmp_path / "books"
    books.mkdir()
    ledger = books / "main.bean"
    ledger.write_text(
        'option "operating_currency" "USD"\n'
        'plugin "load_barrier"\n'
        "2024-01-01 open Assets:Bank USD\n"
        "2024-01-01 open Expenses:Food USD\n"
    )
    ready = tmp_path / "loading.pid"
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "load_barrier.py").write_text(
        textwrap.dedent(
            f"""\
            import os
            import sys
            import time
            from pathlib import Path

            __plugins__ = ("slow_load",)

            def slow_load(entries, options):
                if os.environ.get("LOAD_BARRIER_PROGRAM", "") not in " ".join(sys.orig_argv):
                    return entries, []
                ready = Path({str(ready)!r})
                pending = ready.with_suffix(".pending")
                pending.write_text(str(os.getpid()))
                pending.replace(ready)
                time.sleep(30)
                return entries, []
            """
        )
    )
    env = _env(tmp_path)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(plugins)])
    return ledger, ready, env


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.parametrize(
    ("command", "program"),
    [
        # A bean-check option keeps the native run a clean ledger skips (w5/430).
        pytest.param(["--file", "{ledger}", "check", "--no-cache"], "bean-check", id="check"),
        pytest.param(["query", "--source", "{ledger}", "SELECT count(*)"], "source-query", id="query-source"),
        pytest.param(["doctor", "print-options", "{ledger}"], "bean-doctor", id="doctor"),
        # Control: the JSON-helper path already took its child with it.
        pytest.param(["--file", "{ledger}", "balance", "-x", "units"], "bea_engine", id="balance-control"),
    ],
)
@pytest.mark.parametrize("signal_name", ["SIGTERM", "SIGHUP"])
def test_a_stopped_frontend_leaves_no_engine_child_behind(
    slow_load: tuple[Path, Path, dict[str, str]], command: list[str], program: str, signal_name: str
) -> None:
    ledger, ready, env = slow_load
    env["LOAD_BARRIER_PROGRAM"] = program
    number = int(getattr(signal, signal_name))
    argv = [sys.executable, "-m", "cli.main", *(part.replace("{ledger}", str(ledger)) for part in command)]
    child_pid: int | None = None
    # Its own session, so the signal below reaches the frontend and nothing else.
    with subprocess.Popen(
        argv,
        env=env,
        cwd=ledger.parent,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    ) as process:
        try:
            deadline = time.monotonic() + 30
            while not ready.exists():
                if process.poll() is not None:
                    out, err = process.communicate()
                    pytest.fail(f"bea exited before the ledger load: {process.returncode}\n{out}\n{err}")
                if time.monotonic() >= deadline:
                    pytest.fail("The ledger load never started")
                time.sleep(0.02)
            child_pid = int(ready.read_text())
            assert child_pid != process.pid, "The load must happen in a child for this to test anything"

            process.send_signal(number)
            assert process.wait(timeout=10) == -number

            assert not _alive(child_pid), "The engine child outlived the frontend that started it"
            child_pid = None
            # Nothing is left holding the inherited pipes, so their reader is released too.
            out, _err = process.communicate(timeout=5)
            assert out == ""
        finally:
            if process.poll() is None:
                process.kill()
            if child_pid is not None:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
