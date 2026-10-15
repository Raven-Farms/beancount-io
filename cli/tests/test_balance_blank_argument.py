"""A blank `bea balance` argument names the argument, not a Typer parameter (w5/305).

The refusal said "accounts needs a non-empty value; drop accounts to leave it
unset" — `accounts` is no option anyone can type or drop.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


def _balance(tmp_path: Path, terms: list[str], *flags: str) -> subprocess.CompletedProcess[str]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", *flags, "-f", str(ledger), "balance", *terms],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(("terms", "position"), [([""], 1), (["Cash", ""], 2), ([" "], 1)])
def test_a_blank_argument_is_named_by_position(tmp_path: Path, terms: list[str], position: int) -> None:
    result = _balance(tmp_path, terms)
    assert result.returncode == 2, result.stderr
    assert f"ACCOUNT argument {position} is empty" in result.stderr
    assert "drop accounts" not in result.stderr


def test_json_names_it_too(tmp_path: Path) -> None:
    result = _balance(tmp_path, [""], "--json")
    assert result.returncode == 2
    message = json.loads(result.stdout or result.stderr)["error"]["message"]
    assert message.startswith("ACCOUNT argument 1 is empty") and "drop accounts" not in message
