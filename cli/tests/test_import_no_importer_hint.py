"""The "no importer" refusal suggests the typed account and the file's real columns (w5/470).

It suggested `--account Assets:Checking` and `Date,Amount,Description`
whatever was typed or read, so a pasted command sent savings rows into
checking, on columns no file had.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Savings USD
"""


def _import(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "import", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(("typed", "shown"), [(("--account", "Assets:Savings"), "Assets:Savings"), ((), "ACCOUNT")])
def test_the_hint_keeps_the_typed_account_and_lists_the_header(
    tmp_path: Path, typed: tuple[str, ...], shown: str
) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "sav.csv").write_text("When,What,HowMuch\n2026-02-01,A,-1.00\n")

    result = _import(tmp_path, "sav.csv", *typed)

    assert result.returncode == 2, result.stdout + result.stderr
    flat = " ".join(result.stderr.split())
    assert "Its columns are: When, What, HowMuch." in flat
    assert f"--csv date=COLUMN,amount=COLUMN,narration=COLUMN --account {shown}." in flat
    assert "Assets:Checking" not in flat
    assert "Description" not in flat
