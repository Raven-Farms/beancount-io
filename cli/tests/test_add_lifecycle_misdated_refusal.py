"""A misdated `add open` or `add close` is refused as the write's own dating (w5/772).

A close dated before the account's later postings blamed the valid entry,
citing the unwritten close at a line past the end of the file. A late open
was framed as a pre-existing error, and following the `--allow-errors`
advice wrote the misdated open. Both now name the date bound from the
stranded postings, and neither suggests `--allow-errors`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAINED = """2026-01-01 open Assets:Bank USD
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Equity:Opening USD

2026-01-05 * "Fund"
  Assets:Bank  100 USD
  Equity:Opening

2026-01-20 * "Move out"
  Assets:Cash  100 USD
  Assets:Bank  -100 USD

2026-02-10 * "Lunch"
  Expenses:Food  10 USD
  Assets:Bank
"""
UNOPENED = """2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD

2026-01-10 * "Lunch"
  Expenses:Food  10 USD
  Assets:Cash
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


def test_backdated_close_names_the_last_posting_and_the_bound(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(DRAINED)
    before = ledger.read_bytes()
    result = _bea(tmp_path, "-f", str(ledger), "add", "close", "--date", "2026-02-01", "-a", "Assets:Bank")

    assert result.returncode == 1, result.stderr
    assert ledger.read_bytes() == before
    flat = " ".join((result.stdout + result.stderr).split())
    assert "The proposed close would close Assets:Bank on 2026-02-01; date it on or after 2026-02-10" in flat
    assert "correct the proposed close date" in flat
    assert "main.bean:14" in flat
    assert "main.bean:18" not in flat
    assert "--allow-errors" not in flat


def test_late_open_is_the_writes_own_dating_not_preexisting(tmp_path: Path) -> None:
    ledger = tmp_path / "late.bean"
    ledger.write_text(UNOPENED)
    before = ledger.read_bytes()
    result = _bea(tmp_path, "-f", str(ledger), "add", "open", "--date", "2026-02-01", "-a", "Expenses:Food")

    assert result.returncode == 1, result.stderr
    assert ledger.read_bytes() == before
    flat = " ".join((result.stdout + result.stderr).split())
    assert "The change would leave the ledger invalid" in flat
    assert "date it on or before 2026-01-10" in flat
    assert "already has" not in flat
    assert "--allow-errors" not in flat


def test_allow_errors_does_not_write_the_misdated_open(tmp_path: Path) -> None:
    ledger = tmp_path / "late.bean"
    ledger.write_text(UNOPENED)
    before = ledger.read_bytes()
    result = _bea(
        tmp_path, "-f", str(ledger), "add", "open", "--allow-errors", "--date", "2026-02-01", "-a", "Expenses:Food"
    )

    assert result.returncode == 1, result.stderr
    assert ledger.read_bytes() == before
    flat = " ".join((result.stdout + result.stderr).split())
    assert "would introduce 1 new ledger error" in flat
