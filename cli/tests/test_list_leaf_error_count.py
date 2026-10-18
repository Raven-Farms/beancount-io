"""On an included leaf, `list` counts the errors, not the `--file ROOT` hint (w5/514).

The hint was appended to the error list before it was counted, so `list`
said "Ledger has 3 error(s)" above two errors and the hint, where `balance`
said 2.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("command", [("list", "transaction"), ("balance",)])
def test_the_count_excludes_the_hint(tmp_path: Path, command: tuple[str, ...]) -> None:
    (tmp_path / "2024").mkdir()
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\ninclude "accounts.bean"\ninclude "2024/*.bean"\n'
    )
    (tmp_path / "accounts.bean").write_text("2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n")
    (tmp_path / "2024" / "jan.bean").write_text('2024-01-05 * "Lunch"\n  Expenses:Food 10 USD\n  Assets:Cash\n')
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "2024" / "jan.bean"), *command],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Ledger has 2 error(s)." in result.stderr
    assert "main.bean" in result.stderr  # the hint is still shown
