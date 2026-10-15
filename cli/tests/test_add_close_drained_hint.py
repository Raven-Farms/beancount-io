"""`add close` refused by `check_drained` says to drain the account, not to fix a statement balance (w5/399).

The plugin stamps its zero assertion with the line of the close being
appended, so the failure read as a balance the user typed and got advice
about statement dates and fees for a `close`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """plugin "beancount.plugins.check_drained"
option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "Seed"
  Assets:Cash  100 USD
  Equity:Opening
"""
DRAIN = """2026-01-05 * "Drain"
  Assets:Cash  -100 USD
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
        [sys.executable, "-m", "cli.main", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("fmt", ["text", "json"])
def test_close_of_a_funded_account_names_the_plugin_and_what_remains(tmp_path: Path, fmt: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    before = ledger.read_bytes()
    flags = ("--json",) if fmt == "json" else ()
    result = _bea(
        tmp_path, "-f", str(ledger), *flags, "add", "close", "--account", "Assets:Cash", "--date", "2026-01-10"
    )

    assert result.returncode == 1, result.stderr
    assert ledger.read_bytes() == before
    text = result.stdout + result.stderr
    if fmt == "json":
        text = json.dumps(json.loads(result.stdout or result.stderr))
    flat = " ".join(text.split())
    assert "check_drained" in flat
    assert "still holds 100 USD" in flat
    assert "Move that balance out of Assets:Cash" in flat
    assert "following day" not in flat
    assert "fees" not in flat
    assert "statement" not in flat


def test_close_of_a_drained_account_still_writes(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + DRAIN)
    result = _bea(tmp_path, "-f", str(ledger), "add", "close", "--account", "Assets:Cash", "--date", "2026-01-10")

    assert result.returncode == 0, result.stderr
    assert ledger.read_text().endswith("2026-01-10 close Assets:Cash\n")
