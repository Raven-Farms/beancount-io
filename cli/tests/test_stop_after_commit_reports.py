"""A stop that lands just after the write committed is reported, never a silent death (w5/606).

In the moments after the atomic replace, a forwarded SIGTERM raised
`SystemExit` in the engine before its success envelope was written, and the
frontend re-raised the signal on itself. bea died with no output over a
write that had landed, and a supervisor's retry recorded the entry twice.

A `sitecustomize` on the path holds the engine for a second right after it
replaces `main.bean`, and drops a marker; the stop is sent at that moment.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n'
HOLD_AFTER_COMMIT = """\
import os
import time
from pathlib import Path

_replace = os.replace


def replace(source, target, *args, **kwargs):
    _replace(source, target, *args, **kwargs)
    if Path(target).name == "main.bean" and os.environ.get("TEST_COMMIT_MARKER"):
        Path(os.environ["TEST_COMMIT_MARKER"]).write_text("committed\\n")
        time.sleep(1.0)


os.replace = replace
"""

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX signals")


@pytest.mark.parametrize("stop", [signal.SIGTERM, signal.SIGINT], ids=["SIGTERM", "SIGINT"])
def test_a_stop_right_after_the_commit_reports_the_write(tmp_path: Path, stop: signal.Signals) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "sitecustomize.py").write_text(HOLD_AFTER_COMMIT)
    marker = tmp_path / "committed.marker"
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(shim)]),
        NO_COLOR="1",
        TEST_COMMIT_MARKER=str(marker),
    )
    command = [sys.executable, "-m", "cli.main", "-f", str(ledger), "add", "transaction", "Coffee"]
    command += ["--date", "2026-01-05", "-p", "Expenses:Food 3 USD", "-p", "Assets:Checking"]
    bea = subprocess.Popen(
        command,
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 60
    while not marker.exists() and bea.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert marker.exists(), bea.communicate(timeout=60)
    bea.send_signal(stop)
    out, err = bea.communicate(timeout=60)

    assert bea.returncode == 0, (bea.returncode, out, err)
    assert "Added" in out
    assert "after the write had completed; its result stands" in err
    assert ledger.read_text().count('"Coffee"') == 1


@pytest.mark.parametrize("delay", [0.05, 0.15, 0.25, 0.35, 0.5])
def test_a_stop_at_any_moment_either_writes_nothing_or_reports_the_write(tmp_path: Path, delay: float) -> None:
    """Never both: dying by the signal means nothing was written."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    command = [sys.executable, "-m", "cli.main", "-f", str(ledger), "add", "transaction", "Coffee"]
    command += ["--date", "2026-01-05", "-p", "Expenses:Food 3 USD", "-p", "Assets:Checking"]
    bea = subprocess.Popen(command, env=env, cwd=tmp_path, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
    time.sleep(delay)
    bea.send_signal(signal.SIGTERM)
    out, _ = bea.communicate(timeout=60)

    if bea.returncode == 0:
        assert "Added" in out
        assert ledger.read_text().count('"Coffee"') == 1
    else:
        assert bea.returncode == -signal.SIGTERM
        assert ledger.read_text() == LEDGER
