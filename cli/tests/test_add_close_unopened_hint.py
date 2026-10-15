"""`add close` on an account not open by then gets the remedies other directives get (w5/394).

Upstream says "Unopened account X is being closed" both for a name the
ledger never opens and for an account that opens after the close date.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "Seed"
  Assets:Cash  100 USD
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


def _refused(tmp_path: Path, account: str, date: str) -> str:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    result = _bea(tmp_path, "-f", str(ledger), "add", "close", "--account", account, "--date", date)
    assert result.returncode == 1, result.stderr
    assert ledger.read_text() == LEDGER
    return " ".join(result.stderr.split())


def test_close_before_the_open_names_the_open(tmp_path: Path) -> None:
    flat = _refused(tmp_path, "Assets:Cash", "2025-12-01")
    assert "Unopened account Assets:Cash is being closed" in flat
    assert f"Account opened 2026-01-01 at {tmp_path / 'main.bean'}:2; date the close on or after 2026-01-01." in flat


def test_close_of_a_name_never_opened_suggests_the_near_one(tmp_path: Path) -> None:
    flat = _refused(tmp_path, "Assets:Nope", "2026-02-01")
    assert "Unopened account Assets:Nope is being closed. Did you mean Assets:Cash?" in flat
    assert "bea add open" not in flat


def test_close_of_an_unrelated_name_says_it_is_never_opened(tmp_path: Path) -> None:
    flat = _refused(tmp_path, "Liabilities:Loan", "2026-02-01")
    assert "The ledger never opens Liabilities:Loan; check the account name." in flat
    assert "bea add open" not in flat
