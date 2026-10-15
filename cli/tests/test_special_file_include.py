"""An include that names a FIFO or a device is refused at once (w5/435).

The write snapshot read every include with `read_bytes()`: a FIFO with no
writer blocked every command that loads the ledger forever, and
`include "/dev/zero"` grew the engine to tens of gigabytes. `/dev/null`
still loads as empty.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="FIFOs and /dev paths")


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )


def _ledger(books: Path, include: str) -> None:
    (books / "main.bean").write_text(
        f'option "operating_currency" "USD"\ninclude "{include}"\n2026-01-01 open Assets:Cash USD\n'
    )


@pytest.mark.parametrize(
    "command", [["check"], ["balance"], ["list", "transaction"], ["price", "export", "-o", "out"]], ids=" ".join
)
def test_a_fifo_include_is_refused_at_once(tmp_path: Path, command: list[str]) -> None:
    os.mkfifo(tmp_path / "p.bean")
    _ledger(tmp_path, "p.bean")

    result = _bea(tmp_path, *command)

    assert result.returncode == 2, result.stderr
    assert (
        f"Included file '{tmp_path / 'p.bean'}' (included from '{tmp_path / 'main.bean'}') is not readable: "
        "it is a named pipe, not a file."
    ) in result.stderr


def test_a_device_include_is_refused_and_dev_null_still_loads(tmp_path: Path) -> None:
    _ledger(tmp_path, "/dev/zero")
    zero = _bea(tmp_path, "balance")
    assert zero.returncode == 2, zero.stderr
    assert "Included file '/dev/zero'" in zero.stderr
    assert "is not readable: it is a device, not a file." in zero.stderr

    _ledger(tmp_path, os.devnull)
    assert _bea(tmp_path, "check").returncode == 0
