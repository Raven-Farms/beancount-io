"""The duplicate-entry summary prints amounts in fixed-point notation (w5/383).

`str(Decimal)` wrote `0.00000050 BTC` as `5.0E-7 BTC`; w5/228 fixed the same
interpolation for import rows.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TINY = '2026-01-02 * "tiny"\n  Assets:Cash  0.00000050 BTC\n  Equity:Opening  -0.00000050 BTC\n'
LEDGER = (
    'option "operating_currency" "USD"\nplugin "beancount.plugins.noduplicates"\n'
    "2026-01-01 open Assets:Cash\n2026-01-01 open Equity:Opening\n" + TINY + TINY
)


@pytest.mark.parametrize("command", [("list", "transaction"), ("check",)], ids=["list", "check"])
def test_the_duplicate_summary_reads_the_ledger_s_numbers(tmp_path: Path, command: tuple[str, ...]) -> None:
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

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", "main.bean", *command],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(result.stderr or result.stdout)
    text = json.dumps(payload)
    assert "Duplicate transaction" in text
    assert "Assets:Cash 0.00000050 BTC; Equity:Opening -0.00000050 BTC" in text
    assert "E-7" not in text
