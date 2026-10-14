"""Every global option written after the command gets the placement hint (w5/243).

`--strict`, `--offline` and `--strict-prices` were missing from the examples
table, so they failed with a bare "No such option" while the other global
options said where to put them.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
2024-01-01 open Assets:Cash USD
2024-01-01 open Equity:Opening
2024-01-02 * "Opening"
  Assets:Cash      10.00 USD
  Equity:Opening
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
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
    )


@pytest.mark.parametrize("option", ["--strict", "--offline", "--strict-prices"])
def test_misplaced_global_option_says_where_it_goes(tmp_path: Path, option: str) -> None:
    misplaced = _bea(tmp_path, "-f", "main.bean", "balance", option)
    assert misplaced.returncode == 2
    assert misplaced.stdout == ""
    message = " ".join(misplaced.stderr.split())
    prefix = f"Error: No such option: {option} Place {option} before the command, for example: "
    assert message.startswith(prefix), misplaced.stderr
    example = shlex.split(message.removeprefix(prefix).removesuffix("."))
    assert example[:2] == ["bea", option]

    # The example is runnable as printed: the option is accepted before the command.
    ran = _bea(tmp_path, *example[1:])
    assert ran.returncode == 0, ran.stderr
    assert "No such option" not in ran.stderr


def test_control_json_keeps_its_hint_and_unknown_options_get_none(tmp_path: Path) -> None:
    control = _bea(tmp_path, "-f", "main.bean", "balance", "--json")
    assert control.returncode == 2
    assert " ".join(control.stderr.split()) == (
        "Error: No such option: --json Place --json before the command, for example: bea --json list transaction."
    )

    unknown = _bea(tmp_path, "-f", "main.bean", "balance", "--nosuch")
    assert unknown.returncode == 2
    assert "No such option: --nosuch" in unknown.stderr
    assert "before the command" not in unknown.stderr
