"""The inactive-pad hint mentions `--allow-errors` only when it was passed, once, and names `--pad-from` (w5/395)."""

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


def _refused(tmp_path: Path, *args: str) -> str:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    result = _bea(tmp_path, "-f", str(ledger), "add", *args)
    assert result.returncode == 1, result.stderr
    assert ledger.read_text() == LEDGER
    return " ".join(result.stderr.split())


def test_pad_from_an_unknown_account_names_the_option_not_the_flag(tmp_path: Path) -> None:
    flat = _refused(
        tmp_path,
        *("balance", "--date", "2026-02-05", "--account", "Assets:Cash", "--amount", "150 USD"),
        *("--pad-from", "Equity:Nope"),
    )
    assert "The --pad-from account must be open on the pad date" in flat
    assert "--allow-errors" not in flat
    assert "Pad accounts must be" not in flat


def test_pad_before_both_opens_hints_once_without_the_flag(tmp_path: Path) -> None:
    flat = _refused(tmp_path, "pad", "--date", "2025-12-01", "--account", "Assets:Cash", "--source", "Equity:Opening")
    assert flat.count("Pad accounts must be open on the pad date, 2025-12-01.") == 1
    assert "--allow-errors" not in flat
    assert "The --pad-from account" not in flat


def test_with_the_flag_the_hint_still_says_so_once(tmp_path: Path) -> None:
    flat = _refused(
        tmp_path,
        *("pad", "--date", "2025-12-01", "--account", "Assets:Cash", "--source", "Equity:Opening"),
        "--allow-errors",
    )
    assert flat.count("Pad accounts must be active, even with --allow-errors.") == 1


def test_pad_from_with_the_flag_says_the_flag_does_not_help(tmp_path: Path) -> None:
    flat = _refused(
        tmp_path,
        *("balance", "--date", "2026-02-05", "--account", "Assets:Cash", "--amount", "150 USD"),
        *("--pad-from", "Equity:Nope", "--allow-errors"),
    )
    assert flat.count("The --pad-from account must be open on the pad date, 2026-02-04, even with --allow-errors.") == 1
