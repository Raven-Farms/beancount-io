"""`format` and `ask` refuse two different values for one option (w5/512).

`format` was registered without the shared single-value command, so
`-o a.bean -o b.bean` wrote `b.bean` alone and `-c 40 -c 70` used 70, exit 0.
`ask --into` names a write destination the same way.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-05 * "x"
  Expenses:Food 10 USD
  Assets:Cash
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (("format", "-o", "a.bean", "-o", "b.bean", "main.bean"), "-o 'a.bean' and -o 'b.bean'"),
        (("format", "-c", "40", "-c", "70", "main.bean"), "-c '40' and -c '70'"),
        (("format", "-w", "60", "-w", "80", "main.bean"), "-w '60' and -w '80'"),
        (("-f", "main.bean", "ask", "--into", "a.bean", "--into", "b.bean", "--print", "q"), "--into"),
    ],
    ids=["format-output", "format-currency-column", "format-width", "ask-into"],
)
def test_two_values_are_refused_and_nothing_is_written(tmp_path: Path, args: tuple[str, ...], named: str) -> None:
    result = _bea(tmp_path, *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "Conflicting values for one option" in result.stderr and named in result.stderr
    assert not (tmp_path / "a.bean").exists() and not (tmp_path / "b.bean").exists()
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_the_same_value_twice_is_accepted(tmp_path: Path) -> None:
    result = _bea(tmp_path, "format", "-o", "out.bean", "-o", "out.bean", "main.bean")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out.bean").exists()
