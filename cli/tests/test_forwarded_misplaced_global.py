"""A bea global option after a forwarded command says where it goes (w5/416).

w5/243 gave bea's own commands "Place --offline before the command"; forwarded
natives answered with upstream's bare "No such option" instead.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (books / "main.bean").write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n')
    (books / "bal.txt").write_text("Assets:Cash  5\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("args", "option", "command", "example"),
    [
        (["-f", "main.bean", "check", "--offline"], "--offline", "check", "bea --offline balance"),
        # `--json` there is a dead end: those commands have no JSON output (w5/620).
        (["doctor", "lex", "main.bean", "--debug"], "--debug", "doctor lex", "bea --debug import statement.csv"),
        (["treeify", "bal.txt", "--debug"], "--debug", "treeify", "bea --debug import statement.csv"),
        (
            ["example", "--seed", "1", "-o", "ex.bean", "--debug"],
            "--debug",
            "example",
            "bea --debug import statement.csv",
        ),
        (["-f", "main.bean", "price", "status", "--strict"], "--strict", "price", "bea --strict balance"),
    ],
    ids=["check", "doctor", "treeify", "example", "price"],
)
def test_the_option_is_placed(tmp_path: Path, args: list[str], option: str, command: str, example: str) -> None:
    result = _bea(tmp_path, *args)
    assert result.returncode == 2, result.stderr
    assert (
        f"Error: {option} is a bea option, not one of bea {command}'s. "
        f"Place {option} before the command, for example: {example}.\n"
    ) in result.stderr


@pytest.mark.parametrize(
    "args",
    [["-f", "main.bean", "check", "--json"], ["-f", "main.bean", "check", "-v"], ["treeify", "bal.txt", "-o", "t.txt"]],
    ids=["check-json", "check-verbose", "treeify-output"],
)
def test_a_native_option_still_forwards(tmp_path: Path, args: list[str]) -> None:
    result = _bea(tmp_path, *args)
    assert result.returncode == 0, result.stderr
    assert "is a bea option" not in result.stderr
