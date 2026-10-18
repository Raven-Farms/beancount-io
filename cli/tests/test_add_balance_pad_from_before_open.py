"""`add balance --pad-from` before the account opens names the remedy, not an unused pad (w5/513).

The pad and its assertion are proposed together, so the unused-pad hint
cited the proposed assertion as one at a line past the end of the file that
"already holds", and the pad-account hint never said how to move the date.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Equity:Opening-Balances USD
2024-01-01 open Assets:Cash USD
2024-06-01 open Expenses:Travel USD
"""


def _balance(tmp_path: Path, date: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "add", "balance"]
        + ["-a", "Expenses:Travel", "--amount", "5 USD", "--date", date, "--pad-from", "Equity:Opening-Balances"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_the_refusal_names_the_balance_date_remedy(tmp_path: Path) -> None:
    result = _balance(tmp_path, "2024-06-01")

    assert result.returncode == 1, result.stdout + result.stderr
    flat = " ".join(result.stderr.split())
    assert "Expenses:Travel opens 2024-06-01, after the pad date 2024-05-31" in flat
    assert "Date the balance after the open, for example --date 2024-06-02." in flat
    assert "already holds" not in flat
    assert "need not be added" not in flat
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_following_the_remedy_writes_the_pair(tmp_path: Path) -> None:
    result = _balance(tmp_path, "2024-06-02")

    assert result.returncode == 0, result.stderr
    assert "2024-06-01 pad Expenses:Travel Equity:Opening-Balances" in (tmp_path / "main.bean").read_text()
