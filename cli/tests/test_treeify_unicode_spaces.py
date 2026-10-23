"""`bea treeify` draws an account whose component holds a non-ASCII space (w5/883).

Beancount's lexer takes every non-ASCII character in a component, spaces
included, so `Assets:Bank:My Savings` is a valid account. The wrapper
excluded `\\s` from its classes and left that row flat above the tree.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_treeify_unicode_accounts import _env

SPACES = {"nbsp": " ", "ideographic": "　"}


def _treeify(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "treeify", *args],
        env=_env(tmp_path),
        cwd=tmp_path,
        input=stdin or "",
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("space", list(SPACES.values()), ids=list(SPACES))
def test_an_account_with_a_non_ascii_space_is_drawn_in_its_branch(tmp_path: Path, space: str) -> None:
    table = (
        f"account                   sum\nAssets:Bank:My{space}Savings  1.00 USD\nEquity:Opening           -1.00 USD\n"
    )
    (tmp_path / "balances.txt").write_text(table, encoding="utf-8")

    for result in (
        _treeify(tmp_path, "balances.txt"),
        _treeify(tmp_path, stdin=table),
        _treeify(tmp_path, "balances.txt", "-o", "tree.txt"),
    ):
        assert result.returncode == 0, result.stderr
    drawn = _treeify(tmp_path, "balances.txt").stdout
    assert "|-- Assets\n|   `-- Bank\n|       `-- " in drawn
    assert f"My{space}Savings" in drawn
    # No flat account row above the tree.
    assert not any(line.startswith("Assets:") for line in drawn.splitlines())
    assert (tmp_path / "tree.txt").read_text(encoding="utf-8") == drawn


def test_a_filtered_single_account_still_draws(tmp_path: Path) -> None:
    table = "account                  sum\nAssets:Bank:My Savings  1.00 USD\n"
    result = _treeify(tmp_path, stdin=table)

    assert result.returncode == 0, result.stderr
    assert "My Savings" in result.stdout
