"""`bea treeify` draws accounts under renamed roots (w5/414).

The default pattern kept upstream's five English root names, so the
documented `bea query … > balances.txt; bea treeify balances.txt` pipeline
found "no hierarchical column" on a ledger with `name_assets "Aktiva"`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GERMAN = """option "operating_currency" "EUR"
option "name_assets" "Aktiva"
option "name_equity" "Eigenkapital"
2026-01-01 open Aktiva:Bank:Giro EUR
2026-01-01 open Eigenkapital:Start EUR
2026-01-02 * "x"
  Aktiva:Bank:Giro 10 EUR
  Eigenkapital:Start
"""
ENGLISH = (
    GERMAN.replace("Aktiva", "Assets").replace("Eigenkapital", "Equity").replace('option "name_', '; option "name_')
)


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
    ("ledger", "tree"),
    [
        (GERMAN, ["|-- Aktiva", "|   `-- Bank", "|       `-- Giro", "`-- Eigenkapital", "    `-- Start"]),
        (ENGLISH, ["|-- Assets", "|   `-- Bank", "|       `-- Giro", "`-- Equity", "    `-- Start"]),
    ],
    ids=["renamed-roots", "english-roots"],
)
def test_the_documented_pipeline_draws_the_tree(tmp_path: Path, ledger: str, tree: list[str]) -> None:
    (tmp_path / "main.bean").write_text(ledger)
    balances = _bea(tmp_path, "-f", "main.bean", "query", "SELECT account, sum(position) GROUP BY account")
    assert balances.returncode == 0, balances.stderr
    (tmp_path / "balances.txt").write_text(balances.stdout)

    result = _bea(tmp_path, "treeify", "balances.txt")

    assert result.returncode == 0, result.stderr
    drawn = [line.rstrip() for line in result.stdout.splitlines()]
    for line in tree:
        assert any(row.startswith(line) for row in drawn), (line, drawn)


def test_no_column_names_the_loose_option(tmp_path: Path) -> None:
    (tmp_path / "plain.txt").write_text("just some words\n")
    result = _bea(tmp_path, "treeify", "plain.txt")
    assert result.returncode == 2
    assert "pass -A (loose accounts) or your own -r pattern" in result.stderr
