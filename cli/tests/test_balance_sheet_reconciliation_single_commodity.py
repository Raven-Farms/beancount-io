"""A balance sheet claims a reconciliation only when it is one commodity (w5/505).

`-x at_cost` leaves foreign cash, which has no cost, in its own units, yet
reported `equity_reconciled: true` with a "valuation adjustment" of
`-100.00 EUR 110.00 USD`: the FX trade itself, across unlike commodities.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"

2024-01-01 open Assets:USD USD
2024-01-01 open Assets:EUR EUR
2024-01-01 open Equity:Opening-Balances

2024-01-01 * "Opening"
  Assets:USD 1000.00 USD
  Equity:Opening-Balances

2024-01-10 * "Buy EUR"
  Assets:EUR 100.00 EUR @ 1.10 USD
  Assets:USD -110.00 USD

2024-01-31 price EUR 1.20 USD
"""


def _sheet(tmp_path: Path, conversion: str) -> dict[str, Any]:
    (tmp_path / "fxcost.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "fxcost.bean"), "report", "balance-sheet"]
        + ["-x", conversion],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return dict(json.loads(result.stdout)["data"])


@pytest.mark.parametrize("conversion", ["units", "at_cost"])
def test_a_view_spanning_two_commodities_claims_no_reconciliation(tmp_path: Path, conversion: str) -> None:
    data = _sheet(tmp_path, conversion)

    assert data["net_worth"] == {"EUR": "100.00", "USD": "890.00"}
    assert data["equity_reconciled"] is False
    assert data["valuation_adjustment"] is None


@pytest.mark.parametrize("conversion", ["USD", "at_value"])
def test_a_single_currency_view_still_reconciles(tmp_path: Path, conversion: str) -> None:
    data = _sheet(tmp_path, conversion)

    assert data["equity_reconciled"] is True
    assert list(data["valuation_adjustment"]) == ["USD"]
