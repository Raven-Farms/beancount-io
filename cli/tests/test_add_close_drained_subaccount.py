"""`add close` refused by `check_drained` names the subaccount that holds the money (w5/771).

Balance assertions include subaccounts, but the w5/399 hint attributed the
whole accumulated amount to the closed parent. Following it word for word
posted -100 to the parent while the child kept the money — and `check` then
passed with wrong books.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
plugin "beancount.plugins.check_drained"

2026-01-01 open Assets:Bank USD
2026-01-01 open Assets:Bank:Sub USD
2026-01-01 open Equity:Opening

2026-01-02 * "Fund"
  Assets:Bank:Sub  100 USD
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


def test_close_of_a_parent_names_the_funded_subaccount(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    before = ledger.read_bytes()
    result = _bea(tmp_path, "-f", str(ledger), "add", "close", "--date", "2026-03-01", "-a", "Assets:Bank")

    assert result.returncode == 1, result.stderr
    assert ledger.read_bytes() == before
    flat = " ".join((result.stdout + result.stderr).split())
    assert "Assets:Bank:Sub 100 USD" in flat
    assert "Drain or close Assets:Bank:Sub first" in flat
    assert "Move that balance out of Assets:Bank" not in flat


def test_close_of_a_parent_and_child_names_both(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        LEDGER.replace(
            "  Assets:Bank:Sub  100 USD\n  Equity:Opening\n",
            "  Assets:Bank  50 USD\n  Assets:Bank:Sub  100 USD\n  Equity:Opening  -150 USD\n",
        )
    )
    result = _bea(tmp_path, "-f", str(ledger), "add", "close", "--date", "2026-03-01", "-a", "Assets:Bank")

    assert result.returncode == 1, result.stderr
    flat = " ".join((result.stdout + result.stderr).split())
    assert "Assets:Bank 50 USD, Assets:Bank:Sub 100 USD" in flat
    assert "Drain Assets:Bank and drain or close Assets:Bank:Sub first" in flat
