"""A balance tolerance does not set the file's amount column (w5/271).

Upstream's aligner reads `balance A 1538 ~ 1 USD` as a prefix running up to
the `~` with the tolerance as its number. `add balance` with a tolerance was
therefore appended as `1538 ~        1 USD`, and `format --check` then failed
on a file that had been clean, wanting every older amount moved right.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SEED = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Equity:Opening\n\n"
    '2026-01-02 * "Opening"\n'
    "  Assets:Checking  1538.00 USD\n"
    "  Equity:Opening\n\n"
    "2026-01-03 balance Assets:Checking 1538.00 USD\n"
)
FORMATTED_BALANCE = "2026-01-03 balance Assets:Checking  1538.00 USD"


def _bea(work: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("BEA_") and key != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(work / "config"),
        XDG_CACHE_HOME=str(work / "cache"),
        XDG_DATA_HOME=str(work / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=work,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


def _formatted_ledger(work: Path) -> Path:
    ledger = work / "main.bean"
    ledger.write_text(SEED)
    assert _bea(work, "format", "-i", "main.bean").returncode == 0
    assert _bea(work, "format", "--check", "main.bean").returncode == 0
    return ledger


@pytest.mark.parametrize("extra", [(), ("--pad-from", "Equity:Opening")], ids=["tolerance", "tolerance-with-pad"])
def test_a_formatted_file_stays_formatted_after_a_tolerance_balance(tmp_path: Path, extra: tuple[str, ...]) -> None:
    ledger = _formatted_ledger(tmp_path)
    before = ledger.read_text()
    number = "2000" if extra else "1538"  # A pad is only written when there is a difference to fill.

    added = _bea(
        tmp_path,
        *("-f", "main.bean", "add", "balance", "--date", "2026-02-01"),
        *("--account", "Assets:Checking", "--amount", f"{number} ~ 1 USD", *extra),
    )

    assert added.returncode == 0, added.stderr
    after = ledger.read_text()
    assert after.startswith(before)
    appended = after[len(before) :].splitlines()
    assert f"2026-02-01 balance Assets:Checking {number} ~ 1 USD" in appended
    assert any(line.endswith(" pad Assets:Checking Equity:Opening") for line in appended) is bool(extra)
    check = _bea(tmp_path, "format", "--check", "main.bean")
    assert check.returncode == 0, check.stdout + check.stderr
    assert _bea(tmp_path, "-f", "main.bean", "check").returncode == 0


def test_a_plain_balance_is_still_aligned_to_the_amount_column(tmp_path: Path) -> None:
    ledger = _formatted_ledger(tmp_path)

    added = _bea(
        tmp_path,
        *("-f", "main.bean", "add", "balance", "--date", "2026-02-01"),
        *("--account", "Assets:Checking", "--amount", "1538 USD"),
    )

    assert added.returncode == 0, added.stderr
    assert ledger.read_text().splitlines()[-1] == "2026-02-01 balance Assets:Checking     1538 USD"
    assert _bea(tmp_path, "format", "--check", "main.bean").returncode == 0


@pytest.mark.parametrize("widths", [(), ("-w", "40", "-W", "10"), ("-c", "60")], ids=["automatic", "widths", "column"])
def test_format_leaves_a_hand_written_tolerance_as_written(tmp_path: Path, widths: tuple[str, ...]) -> None:
    tolerance = "2026-02-01 balance Assets:Checking 1538.00 ~ 0.05 USD  ; ~ within a nickel"
    ledger = tmp_path / "main.bean"
    ledger.write_text(SEED + tolerance + "\n")

    formatted = _bea(tmp_path, "format", *widths, "main.bean")

    assert formatted.returncode == 0, formatted.stderr
    lines = formatted.stdout.splitlines()
    assert lines[-1] == tolerance
    if not widths:
        # The assertion no longer decides where every other amount goes.
        assert FORMATTED_BALANCE in lines
