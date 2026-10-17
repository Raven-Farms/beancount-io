"""A zero valuation adjustment and total equity name the conversion currency (w5/506).

Both returned the raw inventory, so an empty one printed "—" and `{}` beside
`Net Worth: 0.00 USD`, though the headline values name the currency.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Bank USD\n2024-01-01 open Equity:Opening-Balances\n'


def _sheet(tmp_path: Path, *flags: str) -> str:
    (tmp_path / "opens.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", *flags, "-f", str(tmp_path / "opens.bean"), "report", "balance-sheet"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_the_text_lines_read_zero_in_the_currency(tmp_path: Path) -> None:
    text = _sheet(tmp_path)

    lines = {line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip() for line in text.splitlines() if ":" in line}
    assert lines["Valuation/translation adjustment (credit)"] == "0.00 USD"
    assert lines["Total equity (credit)"] == "0.00 USD"


def test_the_json_values_name_the_currency(tmp_path: Path) -> None:
    data = json.loads(_sheet(tmp_path, "--json"))["data"]

    assert data["equity_reconciled"] is True
    assert data["valuation_adjustment"] == {"USD": "0"}
    assert data["equity_total"] == {"USD": "0"}
