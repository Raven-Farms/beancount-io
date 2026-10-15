"""A read of a ledger with a managed price include on a full disk gets a bea sentence (w5/408).

The read stages temporary copies beside each ledger file; only a permission
refusal had words for it (w5/095), so a full disk or quota failed every
`balance` with `OSError: [Errno 27] File too large`. A file-size limit
stands in for a full disk.
"""

from __future__ import annotations

import resource
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_price import _cli_env, _managed_ledger, feed_server  # noqa: F401

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="RLIMIT_FSIZE")


def _limited() -> None:
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (256, 256))


def test_a_full_disk_read_names_the_directory(feed_server: str, tmp_path: Path) -> None:  # noqa: F811
    ledger = tmp_path / "main.bean"
    ledger.write_text(_managed_ledger(feed_server) + "".join(f"; padding line {n:04d}\n" for n in range(40)))
    env = _cli_env(tmp_path, feed_server)
    command = [sys.executable, "-m", "cli.main", "-f", str(ledger)]
    primed = subprocess.run([*command, "price", "refresh"], env=env, capture_output=True, text=True, timeout=60)
    assert primed.returncode == 0, primed.stderr

    result = subprocess.run(
        [*command, "balance"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
        preexec_fn=_limited,
    )

    assert result.returncode == 1, result.stderr
    assert f"Cannot read {ledger}: its managed price include" in result.stderr
    assert f"the directory {tmp_path} could not take it (File too large). Free space there" in result.stderr
    assert "OSError" not in result.stderr and "Errno" not in result.stderr
    assert not [path for path in tmp_path.iterdir() if path.name.startswith(".bea-")]
