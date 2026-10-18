"""A stopped frontend export leaves no `.bea-*.tmp` copy behind (w5/608).

`atomic_write` removed its staged copy in a `finally`, but SIGTERM and SIGHUP
kept their default disposition there, which ends the process without running
it: a stopped `format -o` left a full-size hidden copy beside its
destination. A `sitecustomize` holds the frontend at the copy's `fsync`, and
the stop is sent then.
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
MISALIGNED = (
    'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n'
    + "".join(f'2026-01-02 * "lunch {n}"\n  Expenses:Food   {n}.00 USD\n  Assets:Cash\n' for n in range(1, 30))
)
HOLD_AT_FSYNC = """\
import os
import sys
import time
from pathlib import Path

_fsync = os.fsync


def fsync(fd):
    if os.environ.get("TEST_FSYNC_MARKER") and "bea_engine" not in sys.argv[0]:
        Path(os.environ["TEST_FSYNC_MARKER"]).write_text("staged\\n")
        time.sleep(2)
    return _fsync(fd)


os.fsync = fsync
"""

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX signals")


@pytest.mark.parametrize("stop", [signal.SIGTERM, signal.SIGHUP], ids=["SIGTERM", "SIGHUP"])
@pytest.mark.parametrize("existing", [False, True], ids=["new-destination", "existing-destination"])
def test_a_stopped_format_export_leaves_no_staged_copy(tmp_path: Path, stop: signal.Signals, existing: bool) -> None:
    (tmp_path / "mis.bean").write_text(MISALIGNED)
    out = tmp_path / "out" / "aligned.bean"
    out.parent.mkdir()
    if existing:
        out.write_text("kept\n")
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "sitecustomize.py").write_text(HOLD_AT_FSYNC)
    marker = tmp_path / "staged.marker"
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(shim)]),
        NO_COLOR="1",
        TEST_FSYNC_MARKER=str(marker),
    )
    bea = subprocess.Popen(
        [sys.executable, "-m", "cli.main", "format", str(tmp_path / "mis.bean"), "-o", str(out)],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 60
    while not marker.exists() and bea.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert marker.exists(), bea.communicate(timeout=60)
    assert [p.name for p in out.parent.iterdir() if p.name.startswith(".bea-")], "the copy is staged"
    bea.send_signal(stop)
    bea.communicate(timeout=60)

    assert bea.returncode == -stop
    assert [p.name for p in out.parent.iterdir() if p.name.startswith(".bea-")] == []
    if existing:
        assert out.read_text() == "kept\n"
    else:
        assert not out.exists()
