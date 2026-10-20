"""`--pad-from` names the existing pad it would strand, not a consumed cover (w5/797).

When the new pad is needed but would strand an existing one, the fallback
blamed the latest earlier pad even when an earlier assertion had already
consumed it, and its remedy (plain `add balance`) failed. A pad now covers
only while unconsumed for the assertion's currency, and the refusal names
the pad that would go unused with a remedy that works.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:OpeningBalances
2026-01-01 open Equity:Adjust
2026-01-09 pad Assets:Checking Equity:OpeningBalances
2026-01-10 balance Assets:Checking   600.00 USD
2026-01-19 pad Assets:Checking Equity:OpeningBalances
2026-01-20 balance Assets:Checking   650.00 USD
"""


def _bea(ledger: Path, *args: str, as_json: bool = False) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(ledger.parent / "config"),
        XDG_CACHE_HOME=str(ledger.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    command = [sys.executable, "-m", "cli.main"]
    if as_json:
        command.append("--json")
    return subprocess.run(
        [*command, "--no-input", *args],
        env=env,
        cwd=ledger.parent,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_stranded_pad_is_named_with_a_working_remedy(tmp_path: Path) -> None:
    ledger = tmp_path / "chain.bean"
    ledger.write_text(LEDGER)
    before = ledger.read_bytes()

    result = _bea(
        ledger,
        "--file",
        str(ledger),
        "add",
        "balance",
        "--date",
        "2026-01-15",
        "-a",
        "Assets:Checking",
        "--amount",
        "650.00 USD",
        "--pad-from",
        "Equity:Adjust",
        as_json=True,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert (error["category"], error["exit_code"]) == ("validation", 1)
    assert "2026-01-19" in error["message"]
    assert "2026-01-09" not in error["message"]
    assert "2026-01-20" in error["message"]
    assert "Remove that pad first" in " ".join(error["details"])
    assert ledger.read_bytes() == before

    ledger.write_text("\n".join(line for line in LEDGER.splitlines() if "2026-01-19 pad" not in line) + "\n")
    rerun = _bea(
        ledger,
        "--file",
        str(ledger),
        "add",
        "balance",
        "--date",
        "2026-01-15",
        "-a",
        "Assets:Checking",
        "--amount",
        "650.00 USD",
        "--pad-from",
        "Equity:Adjust",
    )
    assert rerun.returncode == 0, rerun.stderr
    assert _bea(ledger, "--file", str(ledger), "check").returncode == 0
