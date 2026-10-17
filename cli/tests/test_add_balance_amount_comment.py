"""`add balance --amount` refuses a `;`, as `add price --amount` does (w5/511).

The text went to the parser unchecked, so the note after `;` was dropped and
the assertion written without it, exit 0.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Bank:Checking USD\n'


def _balance(tmp_path: Path, amount: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "add", "balance"]
        + ["-a", "Assets:Bank:Checking", "--amount", amount, "--date", "2024-03-02", "--allow-errors"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("amount", ["3487.50 USD ; per statement 3480", "3487.50 USD;x", "3487.50 ~ 0.01 USD ; note"])
def test_a_comment_in_the_amount_is_refused(tmp_path: Path, amount: str) -> None:
    result = _balance(tmp_path, amount)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "--amount contains a ';'" in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_a_plain_amount_is_still_written(tmp_path: Path) -> None:
    result = _balance(tmp_path, "0 USD")

    assert result.returncode == 0, result.stderr
    assert "2024-03-02 balance Assets:Bank:Checking" in (tmp_path / "main.bean").read_text()
