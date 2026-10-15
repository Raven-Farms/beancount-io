"""`BEA_ENGINE_PYTHON` naming a directory, a non-executable file or a non-Python is named (w5/309).

w5/269's check passed these by: a directory or a mode-644 file gave a bare
`[Errno 13] Permission denied`, and `/bin/echo` exits 0 without running
anything, so `add` reported an unknown outcome (exit 4) for a write that
never started.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX execute bits")

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n'
NOTE = ("add", "note", "--date", "2026-01-05", "-a", "Assets:Checking", "-m", "e")


def _override(tmp_path: Path, kind: str) -> str:
    if kind == "directory":
        return str(tmp_path)
    if kind == "not-executable":
        path = tmp_path / "noexec"
        path.write_text("x")
        path.chmod(0o644)
        return str(path)
    echo = shutil.which("echo")
    assert echo
    return echo


@pytest.mark.parametrize("kind", ["directory", "not-executable", "not-python"])
@pytest.mark.parametrize("command", [("balance",), NOTE], ids=["balance", "add"])
def test_an_unusable_override_is_named_and_writes_nothing(tmp_path: Path, kind: str, command: tuple[str, ...]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_ENGINE_PYTHON=_override(tmp_path, kind),
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(ledger), *command],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    message = " ".join(result.stderr.split())
    assert result.returncode == 1, result.stderr
    assert "BEA_ENGINE_PYTHON" in message and "Correct or unset BEA_ENGINE_PYTHON" in message
    assert "Errno" not in message and "outcome is unknown" not in message
    assert ledger.read_text() == LEDGER
