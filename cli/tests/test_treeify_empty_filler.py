"""`treeify --filler ''` is refused naming the option, not a ZeroDivisionError (w5/388).

Upstream pads with `filler * (width // len(filler) + 1)`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BALANCES = "Assets:Cash          100 USD\nAssets:Bank:Checking 200 USD\nEquity:Opening      -300 USD\n"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "bal.txt").write_text(BALANCES)
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
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("spelling", [("--filler", ""), ("--filler=",)], ids=["separate", "equals"])
def test_an_empty_filler_is_refused(tmp_path: Path, spelling: tuple[str, ...]) -> None:
    result = _bea(tmp_path, "treeify", "bal.txt", *spelling)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "--filler '' is empty" in result.stderr
    assert "ZeroDivisionError" not in result.stderr


def test_a_one_character_filler_still_draws_the_tree(tmp_path: Path) -> None:
    result = _bea(tmp_path, "treeify", "bal.txt", "--filler", ".")

    assert result.returncode == 0, result.stderr
    assert "Checking" in result.stdout
