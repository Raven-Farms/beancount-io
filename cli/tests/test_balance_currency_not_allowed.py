"""A balance in a currency the account's open excludes says so, without pad advice (w5/350).

Upstream's message ended in a dangling `: `, and bea added the missing-
transactions advice and a `--pad-from` command, neither of which can put a
currency an account excludes into it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Assets:Stock AAPL
2026-01-01 open Equity:Opening
"""


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
        [sys.executable, "-m", "cli.main", *args[:1], "-f", "main.bean", *args[1:]],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_the_refusal_names_the_account_and_drops_pad_advice(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        LEDGER,
        "--no-input",
        "add",
        "balance",
        "--date",
        "2026-03-04",
        "--account",
        "Assets:Stock",
        "--amount",
        "1950 USD",
    )
    message = " ".join(result.stderr.split())
    assert result.returncode == 1
    assert "Invalid currency USD for account 'Assets:Stock': its open does not allow it." in message
    assert "Assets:Stock's open allows AAPL only" in message
    assert "for Balance directive:" not in message
    assert "--pad-from" not in message and "record known fees" not in message
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_an_amount_only_failure_keeps_its_hints(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        LEDGER,
        "--no-input",
        "add",
        "balance",
        "--date",
        "2026-03-04",
        "--account",
        "Assets:Cash",
        "--amount",
        "5 USD",
    )
    assert result.returncode == 1
    assert "--pad-from" in result.stderr


def test_json_check_details_name_the_account(tmp_path: Path) -> None:
    result = _bea(tmp_path, LEDGER + "2026-03-04 balance Assets:Stock  1950 USD\n", "--json", "check")
    assert result.returncode == 1
    details = " ".join(json.loads(result.stdout or result.stderr)["error"]["details"])
    assert "Invalid currency USD for account 'Assets:Stock'" in details
    assert "for Balance directive:" not in details
