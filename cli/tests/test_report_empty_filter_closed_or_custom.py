"""A filter matching no reportable account says so, for a closed or a budget-only account (w5/504).

`report -a Assets:OldCard -t 2025`, for an account closed before the period,
printed only the heading with `account_filter_empty: false`; an account named
only in a `custom "budget"` directive did the same, since that entry passed
the account filter without making any tree.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"

2024-01-01 open Assets:OldCard USD
2024-01-01 open Assets:Bank USD
2024-01-01 open Equity:Opening-Balances

2024-01-01 * "Opening"
  Assets:OldCard 100.00 USD
  Equity:Opening-Balances

2024-06-01 * "Move"
  Assets:Bank 100.00 USD
  Assets:OldCard

2024-06-02 close Assets:OldCard

2025-01-01 custom "budget" Expenses:Travel "monthly" 100.00 USD

2025-02-01 * "Interest"
  Assets:Bank 1.00 USD
  Equity:Opening-Balances
"""


def _report(tmp_path: Path, kind: str, account: str, *flags: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "closed.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", *flags, "-f", str(tmp_path / "closed.bean"), "report", kind]
        + ["-t", "2025", "-a", account],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("account", ["Assets:OldCard", "Expenses:Travel"])
def test_the_empty_filter_is_reported(tmp_path: Path, account: str) -> None:
    text = _report(tmp_path, "trial-balance", account)
    assert text.returncode == 0, text.stderr
    assert f"No accounts match {account}." in text.stdout + text.stderr

    data: dict[str, Any] = json.loads(_report(tmp_path, "trial-balance", account, "--json").stdout)["data"]
    assert data["account_filter_empty"] is True


def test_an_account_outside_this_reports_sections_is_not_empty(tmp_path: Path) -> None:
    data: dict[str, Any] = json.loads(_report(tmp_path, "income-statement", "Assets:Bank", "--json").stdout)["data"]

    assert data["account_filter_empty"] is False
