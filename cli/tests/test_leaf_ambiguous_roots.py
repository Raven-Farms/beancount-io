"""A leaf included by two roots asks which one judges the write (w5/775).

Judged against whichever root sorts first, a true balance was refused and a
false one written with exit 0 — and the refusal never said which root judged
it. Ambiguous writes now exit 2 listing the roots, and an unambiguous
refusal carries the reroute note naming its root.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = """2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Equity:Opening

2026-01-05 * "Opening"
  Assets:Cash  100 USD
  Equity:Opening

include "2026.bean"

2026-01-20 * "Dinner"
  Expenses:Food  30 USD
  Assets:Cash
"""
BACKUP = """2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Equity:Opening

2026-01-05 * "Opening"
  Assets:Cash  100 USD
  Equity:Opening

include "2026.bean"
"""
LEAF = "; 2026\n"
SINGLE_MAIN = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD
include "leaf.bean"
"""
SINGLE_LEAF = """2026-02-01 * "Pay"
  Assets:Cash  10 USD
  Equity:Opening
"""


def _bea(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(cwd / ".config"),
        XDG_CACHE_HOME=str(cwd / ".cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_two_roots_refuse_with_both_named(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "main-backup.bean").write_text(BACKUP)
    (tmp_path / "2026.bean").write_text(LEAF)
    before = (tmp_path / "2026.bean").read_bytes()

    for amount in ("70 USD", "100 USD"):
        result = _bea(
            tmp_path,
            "--file",
            "2026.bean",
            "add",
            "balance",
            "-a",
            "Assets:Cash",
            "--amount",
            amount,
            "--date",
            "2026-02-01",
        )

        assert result.returncode == 2, result.stderr
        flat = " ".join(result.stderr.split())
        assert "2026.bean is included by more than one root ledger" in flat
        assert "main.bean" in flat and "main-backup.bean" in flat
        assert "--into 2026.bean" in flat
    assert (tmp_path / "2026.bean").read_bytes() == before


def test_naming_the_root_writes_through_it(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "main-backup.bean").write_text(BACKUP)
    (tmp_path / "2026.bean").write_text(LEAF)

    result = _bea(
        tmp_path,
        "--file",
        "main.bean",
        "add",
        "balance",
        "--into",
        "2026.bean",
        "-a",
        "Assets:Cash",
        "--amount",
        "70 USD",
        "--date",
        "2026-02-01",
    )

    assert result.returncode == 0, result.stderr
    assert "2026-02-01 balance Assets:Cash  70 USD" in (tmp_path / "2026.bean").read_text()


def test_a_refusal_names_the_root_that_judged_it(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(SINGLE_MAIN)
    (tmp_path / "leaf.bean").write_text(SINGLE_LEAF)

    result = _bea(
        tmp_path,
        "--file",
        "leaf.bean",
        "add",
        "balance",
        "-a",
        "Assets:Cash",
        "--amount",
        "999 USD",
        "--date",
        "2026-03-01",
    )

    assert result.returncode == 1, result.stderr
    assert f"leaf.bean is included by {tmp_path / 'main.bean'}" in result.stderr
