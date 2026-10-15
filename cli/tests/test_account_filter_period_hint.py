"""An account filter that reads as a period points at `-t` (w5/445).

`bea balance 2026-01` matched no account and said only "No accounts match
2026-01." with exit 0, to a user used to another tool's period argument.
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
2026-01-01 open Expenses:Food USD
2026-01-05 * "Lunch"
  Expenses:Food 10 USD
  Assets:Cash
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("args", "note"),
    [
        (["balance", "2026-01"], "No accounts match 2026-01. For the period 2026-01, pass -t 2026-01.\n"),
        (["balance", "FY2026"], "No accounts match FY2026. For the period FY2026, pass -t FY2026.\n"),
        (
            ["balance", "2026-01 - 2026-03"],
            "No accounts match 2026-01 - 2026-03. For the period 2026-01 - 2026-03, pass -t '2026-01 - 2026-03'.\n",
        ),
        (["report", "balance-sheet", "-a", "2026"], "No accounts match 2026. For the period 2026, pass -t 2026.\n"),
        (["balance", "Nope"], "No accounts match Nope.\n"),
        (["report", "balance-sheet", "-a", "Nope"], "No accounts match Nope.\n"),
    ],
)
def test_a_period_shaped_filter_suggests_time(tmp_path: Path, args: list[str], note: str) -> None:
    result = _bea(tmp_path, *args)
    assert result.returncode == 0, result.stderr
    assert note in result.stdout + result.stderr


@pytest.mark.parametrize(("terms", "periods"), [(["2026-01"], ["2026-01"]), (["Nope"], []), (["Food", "2026"], [])])
def test_json_names_the_period_terms_only_when_nothing_matched(
    tmp_path: Path, terms: list[str], periods: list[str]
) -> None:
    result = _bea(tmp_path, "--json", "balance", *terms)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["account_filter_periods"] == periods
