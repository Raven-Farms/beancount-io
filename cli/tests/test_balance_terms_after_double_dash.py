"""`bea balance -- <term>` passes the term to the engine as a filter, never an option (w5/503).

The engine call put the terms before its options with no `--`, so
`-- -Balances` failed the engine call and `-- -f other.bean` reported
another ledger's balances under the original target.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EQ = """option "operating_currency" "USD"
2024-01-01 open Assets:Bank USD
2024-01-01 open Equity:Opening-Balances
2024-01-02 * "o"
  Assets:Bank 100.00 USD
  Equity:Opening-Balances
"""
OTHER = """option "operating_currency" "USD"
2024-01-01 open Assets:Other USD
2024-01-01 open Equity:Opening-Balances
2024-01-01 * "Other"
  Assets:Other 777.00 USD
  Equity:Opening-Balances
"""


def _balance(tmp_path: Path, *terms: str) -> dict[str, Any]:
    (tmp_path / "eq.bean").write_text(EQ)
    (tmp_path / "other.bean").write_text(OTHER)
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
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "eq.bean"), "balance", "--", *terms],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return dict(json.loads(result.stdout))


def test_a_dash_term_is_a_filter(tmp_path: Path) -> None:
    payload = _balance(tmp_path, "-Balances")

    assert payload["data"]["account_filters"] == ["-Balances"]
    assert payload["data"]["equity"]["balance_children"] == {"USD": "-100.00"}


def test_a_file_option_after_double_dash_reads_no_other_ledger(tmp_path: Path) -> None:
    payload = _balance(tmp_path, "-f", str(tmp_path / "other.bean"))

    assert payload["target"]["file"] == str(tmp_path / "eq.bean")
    assert payload["data"]["account_filters"] == ["-f", str(tmp_path / "other.bean")]
    assert "777" not in json.dumps(payload["data"])


def test_a_conversion_option_after_double_dash_is_a_filter(tmp_path: Path) -> None:
    payload = _balance(tmp_path, "-x", "EUR")

    assert payload["data"]["account_filters"] == ["-x", "EUR"]
    assert payload["data"]["conversion"] != "EUR"
