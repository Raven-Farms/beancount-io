"""`GROUP BY 1` on `accounts` gets the w3/358 refusal, not a raw TypeError (w5/313).

The refusal looked only at GROUP BY items with a name, so a positional item
naming the `accounts` target fell through to Beanquery's `issubclass()`
TypeError, exit 1 `validation`.
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
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Equity:Opening
2026-01-05 * "Lunch"
  Expenses:Food  12.50 USD
  Assets:Checking
"""


def _query(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", *args[:-1], "-f", str(tmp_path / "main.bean"), "query", args[-1]],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    "statement", ["SELECT accounts, count(*) GROUP BY 1", "SELECT date, accounts, count(*) GROUP BY 1, 2"]
)
def test_a_positional_group_on_accounts_is_refused(tmp_path: Path, statement: str) -> None:
    result = _query(tmp_path, statement)
    assert result.returncode == 2, result.stderr
    assert "BQL cannot use DISTINCT or GROUP BY on accounts" in result.stderr
    assert "TypeError" not in result.stderr


def test_json_reports_a_usage_error(tmp_path: Path) -> None:
    result = _query(tmp_path, "--json", "SELECT accounts, count(*) GROUP BY 1")
    assert result.returncode == 2
    assert json.loads(result.stdout or result.stderr)["error"]["category"] == "usage"


def test_a_positional_group_on_a_plain_column_still_answers(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT account, count(*) GROUP BY 1")
    assert result.returncode == 0, result.stderr
    assert "Expenses:Food" in result.stdout
