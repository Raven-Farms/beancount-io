"""A stop that lands after a write committed never ends bea silently (w5/825).

The engine handed its stop handlers back to the default disposition as soon
as the command returned, and its answer sat in the pipe buffer until
interpreter shutdown: a stop in those milliseconds killed it, the frontend
saw no exit 0 and died by the signal over a write that had landed, and a
retry recorded the entry twice. The frontend did the same to itself: it
handed its handlers back once the command closed, and a stop during its own
shutdown, after the result had printed, ended it by the signal. A multi-file
`format -i` only noted a stop after its first rewrite, rewrote on until the
frontend's grace period ended in SIGKILL, and nothing said which files had
changed.

Each `sitecustomize` below holds a process at one of those moments and drops
a marker; the stop is sent to `bea` then.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n'
ADD = ["add", "transaction", "Coffee", "--date", "2026-01-05", "-p", "Expenses:Food 3 USD", "-p", "Assets:Checking"]
MISALIGNED = LEDGER + "".join(
    f'2026-01-{day:02d} * "lunch"\n  Expenses:Food   {day}.00 USD\n  Assets:Checking\n' for day in range(2, 9)
)
HOLD_AFTER_ANSWER = """\
import atexit
import os
import sys
import time
from pathlib import Path


def hold():
    if "bea_engine" in sys.argv[0]:
        Path(os.environ["TEST_MARKER"]).write_text("answered\\n")
        time.sleep(1.0)


atexit.register(hold)
"""
HOLD_FRONTEND_AT_EXIT = """\
import atexit
import os
import sys
import time
from pathlib import Path


def hold():
    if sys.argv[0].endswith(os.path.join("cli", "main.py")):
        Path(os.environ["TEST_MARKER"]).write_text("closed\\n")
        time.sleep(1.0)


atexit.register(hold)
"""
HOLD_AFTER_EACH_REPLACE = """\
import os
import sys
import time
from pathlib import Path

_replace = os.replace


def replace(source, target, *args, **kwargs):
    _replace(source, target, *args, **kwargs)
    if "bea_engine" in sys.argv[0] and Path(target).suffix == ".bean":
        Path(os.environ["TEST_MARKER"]).write_text("replaced\\n")
        time.sleep(float(os.environ["TEST_HOLD"]))


os.replace = replace
"""

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX signals")


def _stopped(
    tmp_path: Path, shim_source: str, args: list[str], stop: signal.Signals, hold: float = 0
) -> subprocess.CompletedProcess[str]:
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "sitecustomize.py").write_text(shim_source)
    marker = tmp_path / "held.marker"
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(shim)]),
        NO_COLOR="1",
        TERM="dumb",
        TEST_MARKER=str(marker),
        TEST_HOLD=str(hold),
    )
    bea = subprocess.Popen(
        [sys.executable, "-m", "cli.main", *args],
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
    return subprocess.CompletedProcess(bea.args, bea.returncode, out, err)


@pytest.mark.parametrize("stop", [signal.SIGTERM, signal.SIGHUP, signal.SIGINT], ids=["SIGTERM", "SIGHUP", "SIGINT"])
def test_a_stop_after_the_engine_answered_reports_the_write(tmp_path: Path, stop: signal.Signals) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = _stopped(tmp_path, HOLD_AFTER_ANSWER, ["-f", str(ledger), *ADD], stop)

    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert "Added" in result.stdout
    assert f"Stopped ({stop.name}) after the write had completed; its result stands" in result.stderr
    assert ledger.read_text().count('"Coffee"') == 1


def test_a_stop_while_bea_itself_exits_keeps_the_write_reported(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = _stopped(tmp_path, HOLD_FRONTEND_AT_EXIT, ["-f", str(ledger), *ADD], signal.SIGTERM)

    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert "Added" in result.stdout
    assert ledger.read_text().count('"Coffee"') == 1


def test_a_stop_after_the_engine_answered_keeps_the_json_result(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = _stopped(tmp_path, HOLD_AFTER_ANSWER, ["--json", "-f", str(ledger), *ADD], signal.SIGTERM)

    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert json.loads(result.stdout)["data"]
    assert ledger.read_text().count('"Coffee"') == 1


@pytest.mark.parametrize("structured", [False, True], ids=["text", "json"])
def test_a_stopped_multi_file_format_ends_before_the_next_file_and_names_both(tmp_path: Path, structured: bool) -> None:
    books = tmp_path / "books"
    books.mkdir()
    files = [books / f"{name}.bean" for name in ("a", "b", "c", "d")]
    for file in files:
        file.write_text(MISALIGNED)
    # Each rewrite is held for 3 s: going on to the next file would outrun
    # the frontend's 5 s grace period and end in SIGKILL.
    args = [*(["--json"] if structured else []), "format", "-i", str(books)]

    result = _stopped(tmp_path, HOLD_AFTER_EACH_REPLACE, args, signal.SIGTERM, hold=3.0)

    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    first, *rest = sorted(str(file.resolve()) for file in files)
    if structured:
        error = json.loads(result.stderr)["error"]
        assert "Stopped (SIGTERM) after 1 file(s) formatted; 3 file(s) not attempted" in error["message"]
        assert error["result"]["formatted"] == [first]
        assert error["result"]["not_attempted"] == rest
    else:
        flat = " ".join(result.stderr.split())
        assert "Stopped (SIGTERM) after 1 file(s) formatted; 3 file(s) not attempted" in flat
        assert f"formatted: {first}" in flat
        for name in rest:
            assert f"not attempted: {name}" in flat
    assert [Path(name).read_text() == MISALIGNED for name in [first, *rest]] == [False, True, True, True]


def test_a_writer_killed_after_the_grace_period_reports_an_unknown_outcome(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    # Held past the grace period after the commit, before any answer.
    result = _stopped(tmp_path, HOLD_AFTER_EACH_REPLACE, ["-f", str(ledger), *ADD], signal.SIGTERM, hold=8.0)

    assert result.returncode == 4, (result.returncode, result.stdout, result.stderr)
    assert "outcome is unknown" in result.stderr
    assert "Inspect the file before retrying" in result.stderr
    assert ledger.read_text().count('"Coffee"') == 1
