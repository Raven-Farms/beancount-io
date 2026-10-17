"""`add price` and `add balance` never advise `--allow-errors` for a syntax error (w5/508).

Their strict pre-checks told the user to pass the flag, which never writes
past a syntax error, so the retry failed again with another message.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BROKEN = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Bank:Checking USD\n2024-03-01 bogus line here\n'
UNBALANCED = (
    'option "operating_currency" "USD"\n2024-01-01 open Assets:Bank:Checking USD\n'
    "2024-02-01 balance Assets:Bank:Checking 5 USD\n"
)
COMMANDS = {
    "price": ("add", "price", "-c", "EUR", "--amount", "1.10 USD", "--date", "2024-03-02"),
    "balance": ("add", "balance", "-a", "Assets:Bank:Checking", "--amount", "3487.50 USD", "--date", "2024-03-02"),
}


def _bea(tmp_path: Path, ledger: str, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(ledger)
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("command", list(COMMANDS))
def test_a_syntax_error_is_named_without_the_flag(tmp_path: Path, command: str) -> None:
    result = _bea(tmp_path, BROKEN, *COMMANDS[command])

    assert result.returncode == 1, result.stdout + result.stderr
    assert "including a syntax error" in result.stderr
    assert "Fix the syntax error first: --allow-errors never writes past one." in result.stderr
    assert "Pass --allow-errors to write anyway" not in result.stderr
    assert (tmp_path / "main.bean").read_text() == BROKEN


@pytest.mark.parametrize("command", list(COMMANDS))
def test_other_errors_still_offer_the_flag(tmp_path: Path, command: str) -> None:
    result = _bea(tmp_path, UNBALANCED, *COMMANDS[command])

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Pass --allow-errors to write anyway." in result.stderr
