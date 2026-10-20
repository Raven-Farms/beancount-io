"""A filtered balance sheet presents the same equity split as the unfiltered one (w5/789).

The time clamp closes the period with a conversion transaction booking the
cost residual into `Equity:Conversions:Current`, so `report balance-sheet
-t 2024-01` showed that line with a zero valuation adjustment where the
unfiltered report folds the same amount into the adjustment. The clamp's
synthetic bookings stay out of the sheet's equity tree; the residual
adjustment absorbs them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

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


def _report(tmp_path: Path, *args: str, as_json: bool = False) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    command = [sys.executable, "-m", "cli.main"]
    if as_json:
        command.append("--json")
    return subprocess.run(
        [*command, "-f", "main.bean", "report", "balance-sheet", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _accounts(node: dict[str, Any]) -> set[str]:
    found = {node["account"]}
    for child in node.get("children") or []:
        found |= _accounts(child)
    return found


def test_filtered_and_unfiltered_sheets_match(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    plain = _report(tmp_path)
    assert plain.returncode == 0, plain.stderr
    ranged = _report(tmp_path, "-t", "2024-01")
    assert ranged.returncode == 0, ranged.stderr

    assert ranged.stdout == plain.stdout
    assert "Conversions" not in ranged.stdout
    assert "Valuation/translation adjustment (credit):      -10.00 USD" in ranged.stdout


def test_filtered_and_unfiltered_sheet_payloads_match(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    plain = _report(tmp_path, as_json=True)
    assert plain.returncode == 0, plain.stderr
    ranged = _report(tmp_path, "-t", "2024-01", as_json=True)
    assert ranged.returncode == 0, ranged.stderr
    plain_data = json.loads(plain.stdout)["data"]
    ranged_data = json.loads(ranged.stdout)["data"]

    assert ranged_data["valuation_adjustment"] == {"USD": "-10.0000"}
    assert ranged_data["valuation_adjustment"] == plain_data["valuation_adjustment"]
    assert ranged_data["equity"] == plain_data["equity"]
    assert "Equity:Conversions:Current" not in _accounts(ranged_data["equity"])
