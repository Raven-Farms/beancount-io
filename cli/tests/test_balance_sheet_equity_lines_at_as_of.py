"""The balance sheet's equity lines are judged at the as-of date (w5/127).

A holding bought before its first quote leaves one early net-worth row
unvalued. Every as-of figure was valued, yet the sheet dropped its
"Valuation/translation adjustment" and "Total equity" lines — assets 5,200
against equity -5,000 — and JSON said `equity_reconciled: false`. The same
ledger at a quarterly interval, which has no early row, reconciled.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

UNQUOTED = """option "operating_currency" "USD"
2026-01-01 open Assets:Bank
2026-01-01 open Assets:Broker
2026-01-01 open Equity:Opening

2026-01-02 * "opening"
  Assets:Bank  5000.00 USD
  Equity:Opening

2026-01-15 * "buy"
  Assets:Broker  10 ACME {100.00 USD}
  Assets:Bank  -1000.00 USD
"""
LATE = (
    UNQUOTED
    + """
2026-02-27 price ACME 110.00 USD
2026-03-31 price ACME 120.00 USD
"""
)
# Still unvalued at the as-of date: the period runs past the last entry.
NEVER = (
    UNQUOTED
    + """
2026-03-31 * "top-up"
  Assets:Bank  0.00 USD
  Equity:Opening
"""
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _ledger(tmp_path: Path, text: str) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(text)
    return ledger


def _sheet(tmp_path: Path, ledger: Path, *args: str) -> dict[str, Any]:
    result = _bea(tmp_path, "--json", "--file", str(ledger), "report", "balance-sheet", "--allow-errors", *args)
    assert result.returncode == 0, result.stderr or result.stdout
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def test_row_only_gap_keeps_the_equity_lines(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, LATE)

    monthly = _sheet(tmp_path, ledger)
    assert monthly["net_worth"] == {"USD": "5200.00"}
    assert monthly["valuation_adjustment"] == {"USD": "-200.00"}
    assert monthly["equity_total"] == {"USD": "-5200.00"}
    assert monthly["equity_reconciled"] is True
    # The rows still say what they could not value.
    assert monthly["valuation"] == "partial"
    assert monthly["missing_price_dates"] == [{"from": "ACME", "to": "USD", "date": "2026-01-31"}]
    assert monthly["net_worth_series"][0] == {"date": "2026-01-31", "balance": {"USD": None}}

    # Control: the interval does not decide whether the sheet reconciles.
    quarterly = _sheet(tmp_path, ledger, "--interval", "quarterly")
    assert quarterly["valuation"] == "complete"
    for key in ("valuation_adjustment", "equity_total", "equity_reconciled", "net_worth"):
        assert monthly[key] == quarterly[key], key


def test_row_only_gap_prints_the_equity_lines(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, LATE)

    text = _bea(tmp_path, "--file", str(ledger), "report", "balance-sheet", "--allow-errors")
    assert text.returncode == 0, text.stderr
    lines = {
        label.strip(): amount.strip() for label, _, amount in (line.partition(":") for line in text.stdout.splitlines())
    }
    assert lines["Valuation/translation adjustment (credit)"] == "-200.00 USD"
    assert lines["Total equity (credit)"] == "-5,200.00 USD"
    assert lines["Net Worth"] == "5,200.00 USD"


def test_unvalued_at_as_of_still_withholds_the_equity_lines(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, NEVER)

    for interval in ("monthly", "quarterly"):
        sheet = _sheet(tmp_path, ledger, "--interval", interval)
        assert sheet["net_worth"] == {"USD": None}, interval
        assert sheet["valuation_adjustment"] is None, interval
        assert sheet["equity_total"] is None, interval
        assert sheet["equity_reconciled"] is False, interval

    text = _bea(tmp_path, "--file", str(ledger), "report", "balance-sheet", "--allow-errors")
    assert text.returncode == 0, text.stderr
    assert "Valuation/translation adjustment" not in text.stdout
    assert "Total equity" not in text.stdout
