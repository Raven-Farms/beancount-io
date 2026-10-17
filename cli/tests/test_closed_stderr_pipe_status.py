"""A closed pipe on stderr exits 141, and a usage error keeps exit 2 (w5/522).

Under `2>&1 | head` the broken pipe can be stderr's. Only fd 1 was pointed at
/dev/null, so the shutdown flush of the unwritten stderr line failed and
forced exit 120, and a usage error whose message could not be written exited
1 instead of 2.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food
2026-01-02 * "lunch"
  Expenses:Food 2.50 USD
  Assets:Cash -5.00 USD
"""


def _run_into_closed_pipe(tmp_path: Path, *args: str, both: bool) -> int:
    (tmp_path / "m.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    read_end, write_end = os.pipe()
    os.close(read_end)  # the reader is gone before the child writes a byte
    try:
        child = subprocess.Popen(
            [sys.executable, "-m", "cli.main", "-f", "m.bean", *args],
            cwd=tmp_path,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=write_end if both else subprocess.DEVNULL,
            stderr=write_end,
        )
    finally:
        os.close(write_end)
    return child.wait(timeout=120)


@pytest.mark.parametrize("both", [False, True], ids=["stderr-only", "2>&1"])
def test_a_broken_stderr_pipe_exits_141(tmp_path: Path, both: bool) -> None:
    assert _run_into_closed_pipe(tmp_path, "list", "transaction", "--allow-errors", both=both) == 141


def test_a_usage_error_keeps_exit_2(tmp_path: Path) -> None:
    assert _run_into_closed_pipe(tmp_path, "list", "transaction", "--limit", "0", both=True) == 2
