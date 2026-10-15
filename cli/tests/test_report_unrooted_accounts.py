"""Reports name accounts outside the root ledger's roots instead of dropping them (w5/463).

An include's `option "name_assets" "Aktiva"` applies only while Beancount
parses that include, so `Aktiva:Bank` loaded cleanly but `balance` and the
reports, cut from the root file's five roots, omitted its balance silently.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
include "inc.bean"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:O USD
"""
INC = """option "name_assets" "Aktiva"
2026-01-01 open Aktiva:Bank USD
2026-01-02 * "x"
  Aktiva:Bank 5 USD
  Equity:O
"""


def _bea(tmp_path: Path, *args: str, inc: str = INC) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "inc.bean").write_text(inc)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    flags = [arg for arg in args if arg == "--json"]
    rest = [arg for arg in args if arg != "--json"]
    command = [*flags, "-f", str(tmp_path / "main.bean"), *rest]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *command],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


REPORTS = [["balance"], ["report", "balance-sheet"], ["report", "trial-balance"]]


@pytest.mark.parametrize("command", REPORTS)
def test_text_reports_name_the_account_they_cannot_show(tmp_path: Path, command: list[str]) -> None:
    result = _bea(tmp_path, *command)
    assert result.returncode == 0, result.stderr
    assert "Not shown: 1 account(s) outside the root ledger's account roots: Aktiva:Bank." in result.stderr


@pytest.mark.parametrize("command", REPORTS)
def test_json_reports_list_unrooted_accounts(tmp_path: Path, command: list[str]) -> None:
    result = _bea(tmp_path, "--json", *command)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["unrooted_accounts"] == ["Aktiva:Bank"]


def test_an_ordinary_ledger_reports_none(tmp_path: Path) -> None:
    inc = INC.replace('option "name_assets" "Aktiva"\n', "").replace("Aktiva", "Assets")
    result = _bea(tmp_path, "--json", "balance", inc=inc)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["unrooted_accounts"] == []
    text = _bea(tmp_path, "balance", inc=inc)
    assert "Not shown" not in text.stderr
