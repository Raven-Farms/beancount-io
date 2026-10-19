"""`add balance --pad-from` warns in raw mode, where pads never process (w5/766).

`option "plugin_processing_mode" "raw"` skips pad processing with the
balance checks, so the pad was recorded with exit 0 and silently inserted
nothing. The write still succeeds, but says so.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
option "plugin_processing_mode" "raw"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "funding"
  Assets:Cash  1000.00 USD
  Equity:Opening
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_pad_from_in_raw_mode_warns_and_writes(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea(
        tmp_path,
        "add",
        "balance",
        "--date",
        "2026-01-04",
        "-a",
        "Assets:Cash",
        "--amount",
        "1000.00 USD",
        "--pad-from",
        "Equity:Opening",
    )
    assert result.returncode == 0, result.stderr
    out = result.stderr + result.stdout
    assert 'option "plugin_processing_mode" "raw"' in out
    assert "the pad is recorded but inserts nothing" in out
    text = (tmp_path / "main.bean").read_text()
    assert "pad Assets:Cash Equity:Opening" in text
    assert "2026-01-04 balance Assets:Cash" in text


def test_pad_from_in_default_mode_stays_silent(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER.replace('option "plugin_processing_mode" "raw"\n', ""))
    result = _bea(
        tmp_path,
        "add",
        "balance",
        "--date",
        "2026-01-04",
        "-a",
        "Assets:Cash",
        "--amount",
        "1000.00 USD",
        "--pad-from",
        "Equity:Opening",
    )
    assert result.returncode == 0, result.stderr
    assert "inserts nothing" not in result.stderr + result.stdout
