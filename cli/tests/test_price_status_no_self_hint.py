"""`bea price status` does not tell the user to run `bea price status` (w5/354).

The unavailable-source load warning ends "Run bea price status to inspect the
source." and repeats what the status table's row already says; `check` keeps it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n'
    'include "https://beancount.io/prices/BTC-USD"\n'
    "2026-01-01 open Assets:Cash USD\n"
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--offline", *args[:-1], "-f", "main.bean", *args[-1].split()],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_status_shows_the_table_without_pointing_at_itself(tmp_path: Path) -> None:
    result = _bea(tmp_path, "price status")
    assert result.returncode == 0, result.stderr
    assert "BTC-USD" in result.stdout and "unavailable" in result.stdout
    assert "Run bea price status" not in result.stderr
    as_json = _bea(tmp_path, "--json", "price status")
    assert as_json.returncode == 0 and "Run bea price status" not in as_json.stderr


def test_check_keeps_the_pointer(tmp_path: Path) -> None:
    result = _bea(tmp_path, "check")
    assert "Run bea price status to inspect the source." in " ".join((result.stdout + result.stderr).split())
