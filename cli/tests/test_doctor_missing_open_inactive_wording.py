"""`doctor missing-open` describes an inactive account as Beancount does (w5/139).

A posting dated before its account's `open` was reported as "1 closed
account(s); reopen them", and the number counted error lines, so two postings
to one account read as two accounts.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

EARLY = """\
2026-02-01 open Assets:Cash
2026-01-01 open Equity:Opening
2026-01-15 * "early"
  Assets:Cash  1.00 USD
  Equity:Opening
"""
CLOSED_TWICE = """\
2026-01-01 open Assets:Cash
2026-01-01 open Assets:Bank
2026-01-01 open Equity:Opening
2026-01-10 close Assets:Cash
2026-01-15 * "late"
  Assets:Cash  1.00 USD
  Equity:Opening
2026-01-16 * "later"
  Assets:Cash  1.00 USD
  Assets:Bank
"""
ACTIVE = """\
2026-01-01 open Assets:Cash
2026-01-01 open Equity:Opening
2026-01-15 * "fine"
  Assets:Cash  1.00 USD
  Equity:Opening
"""


def _missing_open(tmp_path: Path, text: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "book.bean").write_text(text)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "doctor", "missing-open", "book.bean"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize(
    ("text", "references"),
    [(EARLY, 1), (CLOSED_TWICE, 2)],
    ids=["before-open", "after-close"],
)
def test_inactive_references_count_distinct_accounts(tmp_path: Path, text: str, references: int) -> None:
    result = _missing_open(tmp_path, text)
    assert result.returncode == 1, result.stderr
    assert result.stdout.count("inactive account 'Assets:Cash'") == references
    message = " ".join(result.stderr.split())
    assert f"{references} reference(s) to 1 inactive account(s)" in message
    assert "before the open date or after the close" in message
    assert "closed account" not in message


def test_an_active_ledger_reports_nothing(tmp_path: Path) -> None:
    result = _missing_open(tmp_path, ACTIVE)
    assert result.returncode == 0, result.stderr
    assert "inactive" not in result.stdout + result.stderr
