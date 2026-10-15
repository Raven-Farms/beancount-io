"""`list` and `query` JSON envelopes say when the answer is partial (w5/460).

Under `--json --allow-errors`, `balance` and `report` carried `ledger_valid`
and `ledger_errors`, but `list` and `query` put the loader errors only in
stderr text, so their envelope looked complete.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BROKEN = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-20 balance Assets:Cash 999 USD
"""
CLEAN = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
"""
READS = [["list", "open"], ["query", "SELECT count(*)"]]


def _read(tmp_path: Path, ledger: str, command: list[str], *flags: str) -> dict:
    (tmp_path / "main.bean").write_text(ledger)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), *command, *flags],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("command", READS)
def test_a_tolerated_error_is_in_the_envelope(tmp_path: Path, command: list[str]) -> None:
    envelope = _read(tmp_path, BROKEN, command, "--allow-errors")
    assert envelope["ledger_valid"] is False
    assert len(envelope["ledger_errors"]) == 1
    assert "main.bean:3: Balance failed for 'Assets:Cash'" in envelope["ledger_errors"][0]


@pytest.mark.parametrize("command", READS)
def test_a_clean_ledger_reads_valid(tmp_path: Path, command: list[str]) -> None:
    envelope = _read(tmp_path, CLEAN, command)
    assert envelope["ledger_valid"] is True
    assert envelope["ledger_errors"] == []
