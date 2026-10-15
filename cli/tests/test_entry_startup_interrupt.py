"""Ctrl-C before the first command runs exits 130 silently, as later (w5/342).

The silent exit lived in the root group's `invoke`; an interrupt while
`cli.main` imported its modules, or while Typer built the command tree, met
Python's default handler: a coloured `KeyboardInterrupt` traceback and death
by SIGINT. The interrupt is raised deterministically at each stage here
rather than raced against a timer.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

DURING_IMPORT = """
import importlib.abc, sys
class Interrupt(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "cli.main":
            raise KeyboardInterrupt
sys.meta_path.insert(0, Interrupt())
"""
DURING_BUILD = """
import typer.main
def interrupted(*args, **kwargs):
    raise KeyboardInterrupt
typer.main.get_command = interrupted
"""


@pytest.mark.parametrize("stage", [DURING_IMPORT, DURING_BUILD], ids=["import", "command-build"])
def test_an_early_interrupt_is_a_silent_130(tmp_path: Path, stage: str) -> None:
    run = "import sys\nsys.argv = ['bea', '--version']\nfrom cli.entry import main\nmain()\n"
    script = textwrap.dedent(stage) + "\n" + run
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={"PYTHONPATH": str(ROOT / "src"), "BEA_NO_UPDATE_NOTIFIER": "1", "BEA_CONFIG_DIR": str(tmp_path)},
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 130, result.stderr
    assert result.stdout == "" and result.stderr == ""


def test_the_console_script_points_at_the_guarded_entry() -> None:
    assert 'bea = "cli.entry:main"' in (ROOT / "pyproject.toml").read_text()
