"""A stopped `price export` leaves its destination as it was (w5/826).

The export replaced its files one at a time, and the first replace committed
the run: a stop after it was only noted, so the engine wrote on until the
frontend's grace period ran out and killed it. The snapshot was left half
written with nothing said, and the retry demanded `--force`. Every file is now
staged before any lands. A `sitecustomize` holds the engine at the second
staged copy's `fsync` for longer than that grace period, and the stop is sent
to `bea` then.
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
MAIN = 'option "operating_currency" "USD"\ninclude "inc/part00.bean"\ninclude "inc/part01.bean"\n'
PART = '2026-01-01 open Assets:Checking{n} USD\n2026-01-02 * "lunch"\n  Assets:Checking{n}  -1.00 USD\n  Equity:Open\n'
HOLD_AT_SECOND_FSYNC = """\
import os
import sys
import time
from pathlib import Path

_fsync = os.fsync
_seen = []


def fsync(fd):
    marker = os.environ.get("TEST_FSYNC_MARKER")
    if marker and "bea_engine" in sys.argv[0]:
        _seen.append(fd)
        if len(_seen) == 2:
            Path(marker).write_text("staged\\n")
            time.sleep(8)
    return _fsync(fd)


os.fsync = fsync
"""

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX signals")


def _env(tmp_path: Path, marker: Path | None = None) -> dict[str, str]:
    shim = tmp_path / "shim"
    shim.mkdir(exist_ok=True)
    (shim / "sitecustomize.py").write_text(HOLD_AT_SECOND_FSYNC)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.pop("TEST_FSYNC_MARKER", None)
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(shim)]),
        TERM="dumb",
        NO_COLOR="1",
    )
    if marker is not None:
        env["TEST_FSYNC_MARKER"] = str(marker)
    return env


def _ledger(tmp_path: Path) -> Path:
    root = tmp_path / "px"
    (root / "inc").mkdir(parents=True)
    (root / "main.bean").write_text(MAIN + "2026-01-01 open Equity:Open\n")
    for n in range(2):
        (root / "inc" / f"part0{n}.bean").write_text(PART.format(n=n))
    return root / "main.bean"


def _listing(directory: Path) -> dict[str, bytes | None]:
    return {
        str(path.relative_to(directory)): path.read_bytes() if path.is_file() else None
        for path in sorted(directory.rglob("*"))
    }


def _stopped_export(tmp_path: Path, ledger: Path, out: Path, stop: signal.Signals, *args: str) -> None:
    marker = tmp_path / "staged.marker"
    marker.unlink(missing_ok=True)
    bea = subprocess.Popen(
        [sys.executable, "-m", "cli.main", "--json", "--offline", "-f", str(ledger), "price", "export", "-o", str(out)]
        + list(args),
        env=_env(tmp_path, marker),
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 90
    while not marker.exists() and bea.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert marker.exists(), bea.communicate(timeout=60)
    bea.send_signal(stop)
    bea.communicate(timeout=60)
    assert bea.returncode != 0


@pytest.mark.parametrize("stop", [signal.SIGTERM, signal.SIGHUP, signal.SIGINT], ids=["SIGTERM", "SIGHUP", "SIGINT"])
def test_a_stopped_export_leaves_no_snapshot_and_the_retry_writes(tmp_path: Path, stop: signal.Signals) -> None:
    ledger = _ledger(tmp_path)
    out = tmp_path / "px-out"

    _stopped_export(tmp_path, ledger, out, stop)

    assert not out.exists(), _listing(out)
    retry = subprocess.run(
        [sys.executable, "-m", "cli.main", "--offline", "-f", str(ledger), "price", "export", "-o", str(out)],
        env=_env(tmp_path),
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert retry.returncode == 0, retry.stderr or retry.stdout
    assert set(_listing(out)) == {"main.bean", "inc", "inc/part00.bean", "inc/part01.bean"}


def test_a_stopped_forced_export_leaves_the_previous_snapshot_unchanged(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    out = tmp_path / "px-out"
    first = subprocess.run(
        [sys.executable, "-m", "cli.main", "--offline", "-f", str(ledger), "price", "export", "-o", str(out)],
        env=_env(tmp_path),
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert first.returncode == 0, first.stderr or first.stdout
    (ledger.parent / "inc" / "part00.bean").write_text(PART.format(n=0) + "; edited\n")
    before = _listing(out)

    _stopped_export(tmp_path, ledger, out, signal.SIGTERM, "--force")

    assert _listing(out) == before
