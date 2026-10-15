"""A misspelled option or unknown command gets a next step (w5/444).

bea rebuilt Click's usage error from `str(exc)`, which drops "(Possible
options: --account)", and names other tools use (`report bs`, `list
account`, `bea help`) ended at a bare "No such command".
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n')
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


def test_a_misspelled_option_keeps_clicks_possibilities(tmp_path: Path) -> None:
    text = _bea(tmp_path, "list", "transaction", "--acount", "Food")
    assert text.returncode == 2
    assert "Error: No such option: --acount (Possible options: --account)\n" in text.stderr

    envelope = _bea(tmp_path, "--json", "list", "transaction", "--acount", "Food")
    assert envelope.returncode == 2
    assert json.loads(envelope.stderr)["error"]["message"] == "No such option: --acount (Possible options: --account)"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["report", "bs"], "No such command 'bs'. Did you mean 'balance-sheet'?"),
        (["report", "pnl"], "No such command 'pnl'. Did you mean 'income-statement'?"),
        (["list", "account"], "No such command 'account'. Did you mean 'open'?"),
        (["list", "txn"], "No such command 'txn'. Did you mean 'transaction'?"),
        (["help"], "No such command 'help'. Did you mean 'bea --help'?"),
        (["report", "zzz"], "No such command 'zzz'. Run 'bea report --help' to list its commands."),
        (["report", "balance_sheet"], "No such command 'balance_sheet'. Did you mean 'balance-sheet'?"),
        (["lsit"], "No such command 'lsit'. Did you mean 'list'?"),
    ],
)
def test_an_unknown_command_names_a_next_step(tmp_path: Path, args: list[str], message: str) -> None:
    result = _bea(tmp_path, *args)
    assert result.returncode == 2
    assert f"Error: {message}\n" in result.stderr
