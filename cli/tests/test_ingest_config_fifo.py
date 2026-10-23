"""`ingest --config` refuses a pipe at once instead of waiting for a writer (w5/885).

The CONFIG preflight read the script before the regular-file check ran, and
opening a named pipe nobody feeds blocks forever.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform == "win32", reason="named pipes are POSIX here")
@pytest.mark.parametrize("operation", [["identify"], ["extract"], ["archive", "--dry-run"]])
def test_an_unfed_config_pipe_is_refused_promptly(tmp_path: Path, operation: list[str]) -> None:
    source = tmp_path / "downloads"
    source.mkdir()
    fifo = tmp_path / "ingest.py"
    os.mkfifo(fifo)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    try:
        # A hang is cut off by the timeout, so a regression fails the test and never stalls the suite.
        result = subprocess.run(
            [sys.executable, "-m", "cli.main", "--no-input", "ingest", *operation, "--config", str(fifo), str(source)],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        fifo.unlink()

    assert result.returncode == 2, result.stderr
    assert "--config" in result.stderr and "is not a regular file" in result.stderr
    assert list(source.iterdir()) == []
