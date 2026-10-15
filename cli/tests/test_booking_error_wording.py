"""Lot-booking errors read as amounts, not namedtuple reprs (w5/333).

Upstream formats `No position matches` and `Cost is negative` with `%s` over
a `Posting` or `Cost`, so refusals carried `CostSpec(...)`, `Decimal(...)`,
`datetime.date(...)` and a meta dict pointing into an unwritten append.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Assets:Broker HOOL
2026-01-01 open Income:Gains USD
2026-01-01 open Equity:Opening
2026-01-03 * "Buy"
  Assets:Broker  10 HOOL {100.00 USD}
  Assets:Cash
"""
WRITTEN = """2026-03-01 * "Sell"
  Assets:Broker  -5 HOOL {999 USD}
  Assets:Cash  600 USD
  Income:Gains
2026-03-02 * "Neg"
  Assets:Broker  3 HOOL {-5 USD}
  Assets:Cash
"""
REPRS = ("Posting(", "CostSpec(", "Cost(", "Decimal(", "datetime.", "meta=")
SELL = ("Sell", "-p", "Assets:Broker -5 HOOL {999 USD}", "-p", "Assets:Cash 600 USD", "-p", "Income:Gains")
NEG = ("Neg", "-p", "Assets:Broker 3 HOOL {-5 USD}", "-p", "Assets:Cash")


def _bea(tmp_path: Path, ledger: str, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(ledger)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _details(result: subprocess.CompletedProcess[str]) -> str:
    assert result.returncode == 1, result.stdout + result.stderr
    return " ".join(json.loads(result.stdout or result.stderr)["error"]["details"])


@pytest.mark.parametrize(
    ("posting", "expected"),
    [
        (SELL, "No position matches -5 HOOL {999 USD} in Assets:Broker; it holds (10 HOOL {100.00 USD, 2026-01-03})"),
        (NEG, "Cost is negative: -5 USD"),
    ],
    ids=["no-lot", "negative-cost"],
)
def test_an_add_refusal_reads_as_amounts(tmp_path: Path, posting: tuple[str, ...], expected: str) -> None:
    details = _details(_bea(tmp_path, LEDGER, "add", "transaction", posting[0], "--date", "2026-03-01", *posting[1:]))
    assert expected in details
    for repr_ in REPRS:
        assert repr_ not in details
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_json_check_details_read_as_amounts(tmp_path: Path) -> None:
    details = _details(_bea(tmp_path, LEDGER + WRITTEN, "check"))
    assert "main.bean:9: No position matches -5 HOOL {999 USD} in Assets:Broker" in details
    assert "main.bean:14: Cost is negative: -5 USD" in details
    for repr_ in REPRS:
        assert repr_ not in details
