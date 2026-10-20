"""Closed-account hints name the close and the right remedy (w5/773).

`add open` on a closed account said only "an account opens once"; `doctor
missing-open` said to "reopen the account", which Beancount cannot do; and a
duplicate `add close` got upstream's bare message, or blamed the close
already in the file.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSED = """2026-01-01 open Assets:Old USD
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD

2026-01-05 * "Fund"
  Assets:Old  100 USD
  Equity:Opening

2026-01-20 * "Move out"
  Assets:Cash  100 USD
  Assets:Old  -100 USD

2026-02-01 close Assets:Old
"""
BROKEN = (
    CLOSED
    + """
2026-03-05 * "Late"
  Assets:Old  5 USD
  Assets:Cash
"""
)


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


def _flat(result: subprocess.CompletedProcess[str]) -> str:
    return " ".join((result.stdout + result.stderr).split())


def test_missing_open_says_to_move_the_close_later(tmp_path: Path) -> None:
    ledger = tmp_path / "broken.bean"
    ledger.write_text(BROKEN)
    result = _bea(tmp_path, "doctor", "missing-open", str(ledger))

    assert result.returncode == 1, result.stderr
    flat = _flat(result)
    assert "move the open earlier, move the close later, or fix the postings" in flat
    assert "reopen" not in flat


def test_duplicate_open_on_a_closed_account_names_the_close(tmp_path: Path) -> None:
    ledger = tmp_path / "broken.bean"
    ledger.write_text(BROKEN)
    result = _bea(
        tmp_path,
        "-f",
        str(ledger),
        "add",
        "open",
        "--date",
        "2026-03-01",
        "-a",
        "Assets:Old",
        "-c",
        "USD",
        "--allow-errors",
    )

    assert result.returncode == 1, result.stderr
    flat = _flat(result)
    assert "an account opens once" in flat
    assert f"It is closed 2026-02-01 at {ledger}:13; remove that close or date it later" in flat


def test_widening_open_on_a_closed_account_names_the_close(tmp_path: Path) -> None:
    ledger = tmp_path / "broken.bean"
    ledger.write_text(BROKEN)
    result = _bea(
        tmp_path,
        "-f",
        str(ledger),
        "add",
        "open",
        "--date",
        "2026-03-01",
        "-a",
        "Assets:Old",
        "-c",
        "EUR",
        "--allow-errors",
    )

    assert result.returncode == 1, result.stderr
    flat = _flat(result)
    assert "To allow EUR too" in flat
    assert f"It is closed 2026-02-01 at {ledger}:13; remove that close or date it later" in flat


def test_duplicate_close_names_the_existing_close(tmp_path: Path) -> None:
    ledger = tmp_path / "b.bean"
    ledger.write_text(CLOSED)
    later = _bea(tmp_path, "-f", str(ledger), "add", "close", "--date", "2026-03-01", "-a", "Assets:Old")
    earlier = _bea(tmp_path, "-f", str(ledger), "add", "close", "--date", "2026-01-25", "-a", "Assets:Old")

    assert later.returncode == 1, later.stderr
    assert earlier.returncode == 1, earlier.stderr
    assert "Proposed append (not written): Duplicate close directive for Assets:Old" in _flat(later)
    for result, date in ((later, "2026-03-01"), (earlier, "2026-01-25")):
        flat = _flat(result)
        assert f"The proposed close would close Assets:Old on {date}, but it is already closed" in flat
        assert f"2026-02-01 at {ledger}:13; an account closes once" in flat
        assert "edit that close's date" in flat
