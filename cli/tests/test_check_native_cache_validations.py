"""Text `bea check` keeps bean-check's data-type validation once a load is cached (w5/564).

Beancount caches a load that takes over a second, and the cache key ignores
the validations a load ran. The helper's load wrote that cache without
bean-check's data-type checks, native bean-check then read it, and a ledger
bean-check rejects exited 0 with no output, on the first run and every run after.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = """import time
from beancount.core import data
__plugins__ = ["slowbad"]
def slowbad(entries, options_map):
    time.sleep(1.2)  # past Beancount's one-second threshold, so the load is cached
    return [e._replace(tags=None) if isinstance(e, data.Transaction) and e.narration == "BAD" else e
            for e in entries], []
"""
LEDGER = """option "insert_pythonpath" "TRUE"
plugin "slowbad"
2020-01-01 open Assets:Cash USD
2020-01-01 open Expenses:Food USD
2020-06-01 * "BAD"
  Expenses:Food  1 USD
  Assets:Cash
"""


def test_a_cached_load_still_fails_bean_checks_data_type_validation(tmp_path: Path) -> None:
    (tmp_path / "slowbad.py").write_text(PLUGIN)
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BEA_", "BEANCOUNT_")) and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )

    def bea(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "cli.main", "--file", str(ledger), *args],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )

    # Any slow read caches the load, with the validations a read runs.
    assert bea("list", "transaction").returncode in (0, 1)
    assert any((tmp_path / "cache").rglob("*.picklecache")), "the slow load should have been cached"

    for run in (bea("check"), bea("check")):
        assert run.returncode == 1, run.stdout + run.stderr
        assert "main.bean:5: Invalid data types: Invalid tags type" in run.stdout + run.stderr
