"""A load cache stock Beancount wrote is not served to `bea`'s own reads (w5/220).

`bean-doctor`, `bean-check` and an editor's Beancount read a ledger's bytes as
they are; `bea` reads them BOM-stripped and NFC-normalized. On a ledger slow
enough to be cached, a stock tool's cache was then trusted by every later
read: a query for `'Café Luna'` found nothing with exit 0 after `bea doctor`,
and a valid BOM-marked ledger failed `bea check`, until a ledger file changed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from cli.engine import launch

ROOT = Path(__file__).resolve().parents[1]

# Beancount caches a load only when it took a second; this plugin makes a
# short ledger that slow without sixty thousand transactions.
SLOW_PLUGIN = """\
import time

__plugins__ = ["slow"]


def slow(entries, options_map):
    time.sleep(1.05)
    return entries, []
"""
# The payee is spelled decomposed in the file and composed in the query.
LEDGER = (
    'option "title" "w5/220"\n'
    'option "insert_pythonpath" "TRUE"\n'
    'plugin "w5_220_slow"\n'
    "2000-01-01 open Assets:Bank USD\n"
    "2000-01-01 open Expenses:Food USD\n"
    '2021-03-01 * "Café Luna" "lunch"\n'
    "  Expenses:Food  12.50 USD\n"
    "  Assets:Bank\n"
)
QUERY = "SELECT sum(position) AS spent WHERE payee ~ 'Café Luna' AND account ~ 'Food'"


def _ledger(tmp_path: Path, *, bom: bool = False) -> Path:
    (tmp_path / "w5_220_slow.py").write_text(SLOW_PLUGIN)
    ledger = tmp_path / "main.bean"
    ledger.write_text(("﻿" if bom else "") + LEDGER, encoding="utf-8")
    return ledger


def _env() -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": str(ROOT / "src"), "NO_COLOR": "1"}


def _bea(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _stock_check(ledger: Path) -> subprocess.CompletedProcess[str]:
    """Stock `bean-check`, pointed at the cache `bea` uses for this ledger."""
    return subprocess.run(
        [str(launch.native_command("bean-check")), str(ledger)],
        env={**_env(), launch.LOAD_CACHE_ENV: launch.load_cache_pattern(ledger)},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _cache(ledger: Path) -> Path:
    return Path(launch.load_cache_pattern(ledger).format(filename=ledger.name))


def test_composed_literal_still_matches_after_doctor(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    doctor = _bea("doctor", "missing-open", str(ledger))
    assert doctor.returncode == 0, doctor.stderr
    assert _cache(ledger).exists(), "the fixture must be slow enough to be cached"

    result = _bea("--file", str(ledger), "query", QUERY)

    assert result.returncode == 0, result.stderr
    assert "12.50 USD" in result.stdout


def test_bom_ledger_still_checks_after_a_stock_load(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, bom=True)

    stock = _stock_check(ledger)
    assert stock.returncode == 1, "stock bean-check cannot parse the mark"
    assert "Invalid token" in stock.stderr
    assert _cache(ledger).exists(), "the fixture must be slow enough to be cached"

    checked = _bea("--json", "--file", str(ledger), "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert json.loads(checked.stdout)["data"] == {"valid": True, "errors": []}
    plain = _bea("--file", str(ledger), "check")
    assert plain.returncode == 0, plain.stdout + plain.stderr


def test_engine_reads_keep_reusing_their_own_cache(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    first = _bea("--file", str(ledger), "query", QUERY)
    assert "12.50 USD" in first.stdout, first.stderr
    assert _cache(ledger).exists(), "the fixture must be slow enough to be cached"
    written = _cache(ledger).stat()

    # Stock tools read the engine's cache and leave it as it is.
    assert _bea("--file", str(ledger), "check").returncode == 0
    assert _bea("doctor", "missing-open", str(ledger)).returncode == 0
    balance = _bea("--json", "--file", str(ledger), "balance", "Expenses")
    assert balance.returncode == 0, balance.stderr
    again = _bea("--file", str(ledger), "query", QUERY)

    assert "12.50 USD" in again.stdout, again.stderr
    now = _cache(ledger).stat()
    assert (now.st_mtime_ns, now.st_size, now.st_ino) == (written.st_mtime_ns, written.st_size, written.st_ino)
