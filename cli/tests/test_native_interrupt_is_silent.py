"""Ctrl-C during a forwarded upstream program exits 130 without a message (w5/273).

`USAGE.md`: "`Ctrl-C` still exits 130 and a closed downstream pipe still exits
141, both without a message." `bea check` and the forwarded `bea doctor`
operations hand their streams to `bean-check` / `bean-doctor`, and the terminal
sends SIGINT to the whole foreground process group — so the Click child printed
`Aborted!` under the `^C` before the frontend's own interrupt stopped it.

The terminal cases need a real PTY: only there does one key reach both
processes. A plugin holds the upstream program inside its load, so the
interrupt lands on the forwarded child and never on the helper pass before it.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from cli.engine import launch
from tests.test_interrupt_contract import BEA, _child_env, _interrupt_at, _noise

#: Stalls only the forwarded upstream program, and says once it is inside it.
PLUGIN = """\
import os, sys, time

__plugins__ = ["hold"]


def hold(entries, options_map):
    if os.path.basename(sys.argv[0]) in ("bean-check", "bean-doctor"):
        with open(os.path.join(os.path.dirname(__file__), "child.pid"), "w") as record:
            record.write(str(os.getpid()))
        print("LOADING", file=sys.stderr, flush=True)
        time.sleep(120)
    return entries, []
"""

LEDGER = 'option "insert_pythonpath" "TRUE"\nplugin "hold_load"\n2026-01-01 open Assets:Cash USD\n'


@pytest.fixture
def held(tmp_path: Path) -> Path:
    (tmp_path / "hold_load.py").write_text(PLUGIN, encoding="utf-8")
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def _gone(pid: int, *, within: float = 10.0) -> bool:
    deadline = time.time() + within
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


@pytest.mark.parametrize(
    "argv",
    [
        # A plain `check` of a clean ledger answers from the helper's load and
        # never starts bean-check (w5/430); an option keeps the forwarded run.
        pytest.param(["--file", "main.bean", "check", "--verbose"], id="check-native-option"),
        pytest.param(["doctor", "context", "main.bean", "3"], id="doctor"),
    ],
)
def test_ctrl_c_during_a_forwarded_program_exits_130_silently(tmp_path: Path, held: Path, argv: list[str]) -> None:
    status, screen = _interrupt_at(tmp_path, argv, expect="LOADING")

    assert status == 130, f"expected the documented interrupt status; screen was {screen!r}"
    assert "Aborted!" not in screen
    assert "Traceback" not in screen
    assert _noise(screen) == "", f"a deliberate Ctrl-C prints nothing; got {screen!r}"
    # The child no longer hears the key itself, so the frontend has to end it.
    assert _gone(int((tmp_path / "child.pid").read_text())), "the upstream program outlived the interrupt"


def test_an_uninterrupted_check_still_passes_upstream_through(tmp_path: Path) -> None:
    """The control: streams and status are still upstream's own."""
    good = tmp_path / "good.bean"
    good.write_text("2026-01-01 open Assets:Cash USD\n", encoding="utf-8")
    bad = tmp_path / "bad.bean"
    bad.write_text("2026-01-01 open Assets:Cash USD\n2026-01-02 close Assets:Bank\n", encoding="utf-8")

    def check(ledger: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(BEA), "--file", str(ledger), "check"],
            cwd=tmp_path,
            env=_child_env(tmp_path),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    passed = check(good)
    assert (passed.returncode, passed.stdout, passed.stderr) == (0, "", "")
    failed = check(bad)
    assert failed.returncode == 1
    assert "Assets:Bank" in failed.stderr


#: Exits 7 when it was started with SIGINT blocked, 0 when it can still hear it.
REPORTS_ITS_MASK = "import signal, sys; sys.exit(7 * (signal.SIGINT in signal.pthread_sigmask(signal.SIG_BLOCK, [])))"


def test_only_an_upstream_program_is_started_deaf_to_ctrl_c(monkeypatch: pytest.MonkeyPatch) -> None:
    """The helper cleans up after an interrupt itself, so it must keep hearing one."""
    monkeypatch.setattr(launch, "native_command", lambda name: Path(sys.executable))
    monkeypatch.setattr(launch, "helper_command", lambda: ([sys.executable, "-c", REPORTS_ITS_MASK], None))
    before = signal.getsignal(signal.SIGINT)

    assert launch.run_native("bean-check", ["-c", REPORTS_ITS_MASK], env=dict(os.environ)) == 7
    assert launch.run_engine_argv(["check"]) == 0
    # Nothing of it is left on the frontend.
    assert signal.getsignal(signal.SIGINT) is before
    assert signal.SIGINT not in signal.pthread_sigmask(signal.SIG_BLOCK, [])


def test_the_frontends_own_interrupt_still_ends_a_deaf_child(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ctrl-C reaches the frontend as before, and takes the child with it."""
    child = "import os, signal, time; os.kill(os.getppid(), signal.SIGINT); time.sleep(120)"
    monkeypatch.setattr(launch, "native_command", lambda name: Path(sys.executable))
    started = time.time()

    with pytest.raises(KeyboardInterrupt):
        launch.run_native("bean-check", ["-c", child], env=dict(os.environ))

    assert time.time() - started < 60, "the child was waited out instead of stopped"
    assert signal.SIGINT not in signal.pthread_sigmask(signal.SIG_BLOCK, [])
