"""A user regex Python would read other than as written is refused (w5/429).

Python's regex has no POSIX classes: `[[:alpha:]]` is a set of `[`, `:` and
letters, and Python only warns "Possible nested set". `query ~`, `report -a`
and `treeify -r` leaked that `FutureWarning`, with a source path, and then
ran with the other meaning: no rows, an empty report, a split on something
else, all with exit 0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "x"
  Expenses:Food 5 USD
  Assets:Cash
"""
POSIX = "[:alpha:] is a POSIX class, which Python's regex does not have"


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (books / "main.bean").write_text(LEDGER)
    (books / "bal.txt").write_text("Assets:Cash  5\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "PYTHONWARNINGS"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["query", "SELECT account WHERE account ~ '[[:alpha:]]'"], f"in the pattern '[[:alpha:]]', {POSIX}"),
        (["report", "balance-sheet", "-a", "[[:alpha:]]"], f"Invalid account filter '[[:alpha:]]': {POSIX}"),
        (["treeify", "-r", "[[:alpha:]]+", "bal.txt"], f"--pattern '[[:alpha:]]+': {POSIX}"),
        (
            ["query", "SELECT account WHERE account ~ '[[a]'"],
            "Python's regex reads it differently from what it says (Possible nested set at position 1)",
        ),
    ],
    ids=["query-posix", "report", "treeify", "query-nested-set"],
)
def test_the_pattern_is_refused_in_bea_words(tmp_path: Path, args: list[str], message: str) -> None:
    result = _bea(tmp_path, *args)
    assert result.returncode == 2, result.stdout + result.stderr
    assert message in result.stderr
    assert "FutureWarning" not in result.stderr
    assert "warning:" not in result.stderr.lower()


def test_json_names_it_too(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json", "query", "SELECT account WHERE account ~ '[[:alpha:]]'")
    assert result.returncode == 2
    assert POSIX in json.loads(result.stderr)["error"]["message"]
    assert result.stdout == ""


@pytest.mark.parametrize(
    "args",
    [
        ["query", "SELECT account WHERE account ~ 'Food'"],
        ["report", "balance-sheet", "-a", "Assets"],
        ["treeify", "-r", "[A-Z][a-z]+", "bal.txt"],
    ],
    ids=["query", "report", "treeify"],
)
def test_ordinary_patterns_are_unchanged(tmp_path: Path, args: list[str]) -> None:
    result = _bea(tmp_path, *args)
    assert result.returncode == 0, result.stderr
    assert "FutureWarning" not in result.stderr
