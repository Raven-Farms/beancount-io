"""Options with a fixed vocabulary complete their values, and fish gets one candidate per line (w5/421).

`--format`, `--shell`, `--booking`, `--flag`, `engine enable` and the `price`
verbs completed as file names, and Typer's fish formatter wrapped long option
help onto lines without a tab, which fish offered as candidates. Driven
through the Click/Typer completion protocol; nothing is installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

BEA = shutil.which("bea", path=str(Path(__file__).resolve().parents[1] / ".venv" / "bin"))

pytestmark = pytest.mark.skipif(BEA is None, reason="needs the bea console script")


def _complete(shell: str, line: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in ("COLUMNS", "TERMINAL_WIDTH")}
    env.update(_BEA_COMPLETE=f"complete_{shell}", _TYPER_COMPLETE_ARGS=line, BEA_NO_UPDATE_NOTIFIER="1")
    if shell == "fish":
        env["_TYPER_COMPLETE_FISH_ACTION"] = "get-args"
    assert BEA is not None
    return subprocess.run([BEA], env=env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL).stdout


@pytest.mark.parametrize(
    ("line", "values"),
    [
        ("bea query --format ", ["text", "csv", "beancount"]),
        ("bea --shell ", ["bash", "zsh", "fish", "powershell", "pwsh"]),
        ("bea add open --booking ", ["STRICT", "STRICT_WITH_SIZE", "NONE", "FIFO", "LIFO", "HIFO"]),
        ("bea add transaction --flag ", ["*", "!"]),
        ("bea engine enable ", ["beangulp", "beanprice"]),
        ("bea price ", ["status", "refresh", "export"]),
    ],
    ids=["format", "shell", "booking", "flag", "engine-enable", "price"],
)
def test_a_fixed_vocabulary_completes_its_values(line: str, values: list[str]) -> None:
    offered = _complete("zsh", line)
    assert "_files" not in offered
    for value in values:
        assert f'"{value}"' in offered, offered


def test_a_prefix_narrows_the_values() -> None:
    assert _complete("zsh", "bea query --format c").strip() == """_arguments '*: :(("csv"))'"""


def test_fish_gets_one_candidate_per_line() -> None:
    lines = [line for line in _complete("fish", "bea list transaction --").splitlines() if line]
    assert lines
    assert all("\t" in line for line in lines), [line for line in lines if "\t" not in line]
