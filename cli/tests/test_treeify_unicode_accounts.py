"""`bea treeify` draws account components with non-ASCII letters (w5/137).

Upstream's default pattern takes ASCII only, so a row such as
`Assets:Bank:Épargne` was left flat in the middle of the tree — sometimes above
its own parent — while the command exited 0.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

ACCENTED = (
    "account               sum\n"
    "Assets:Bank:Checking  500.00 CNY\n"
    "Assets:Bank:Épargne    50.00 CNY\n"
    "Expenses:Food:Café      5.00 CNY\n"
    "Expenses:Food:Lunch    30.00 CNY\n"
)
ACCENTED_TREE = (
    "account               sum\n"
    "|-- Assets\n"
    "|   `-- Bank\n"
    "|       |-- Checking  500.00 CNY\n"
    "|       `-- Épargne    50.00 CNY\n"
    "`-- Expenses\n"
    "    `-- Food\n"
    "        |-- Café        5.00 CNY\n"
    "        `-- Lunch      30.00 CNY\n"
)
ASCII = ACCENTED.replace("É", "E").replace("é", "e")
ASCII_TREE = ACCENTED_TREE.replace("É", "E").replace("é", "e")

CJK_LEDGER = (
    "2024-01-01 open Assets:B银行:Checking CNY\n"
    "2024-01-01 open Assets:B银行:C储蓄 CNY\n"
    "2024-01-01 open Expenses:F餐饮:L午餐 CNY\n"
    "2024-01-01 open Equity:Opening CNY\n"
    '2024-01-02 * "Opening"\n'
    "  Assets:B银行:Checking   70.00 CNY\n"
    "  Assets:B银行:C储蓄      500.00 CNY\n"
    "  Expenses:F餐饮:L午餐     30.00 CNY\n"
    "  Equity:Opening\n"
)


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONIOENCODING="utf-8",
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _bea(tmp_path: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=_env(tmp_path),
        cwd=tmp_path,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def test_accented_components_are_drawn_under_their_parents(tmp_path: Path) -> None:
    (tmp_path / "bal.txt").write_text(ACCENTED, encoding="utf-8")

    result = _bea(tmp_path, "treeify", "bal.txt")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ACCENTED_TREE


def test_stdin_and_output_file_take_the_same_pattern(tmp_path: Path) -> None:
    piped = _bea(tmp_path, "treeify", stdin=ACCENTED)
    written = _bea(tmp_path, "treeify", "-o", "tree.txt", stdin=ACCENTED)

    assert piped.returncode == 0, piped.stderr
    assert piped.stdout == ACCENTED_TREE
    assert written.returncode == 0, written.stderr
    assert (tmp_path / "tree.txt").read_text(encoding="utf-8") == ACCENTED_TREE


def test_the_ascii_control_is_unchanged(tmp_path: Path) -> None:
    """The same tree upstream's own default pattern draws, spelled out with `-r`."""
    upstream_default = r"(Assets|Liabilities|Equity|Income|Expenses)(:[A-Z0-9][A-Za-z0-9-_']*)*"

    default = _bea(tmp_path, "treeify", stdin=ASCII)
    explicit = _bea(tmp_path, "treeify", "-r", upstream_default, stdin=ASCII)

    assert default.returncode == 0, default.stderr
    assert default.stdout == ASCII_TREE
    assert explicit.stdout == default.stdout


def test_real_query_output_with_cjk_accounts_is_a_whole_tree(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(CJK_LEDGER, encoding="utf-8")
    query = _bea(
        tmp_path,
        "--file",
        "main.bean",
        "query",
        "SELECT account, sum(position) GROUP BY account ORDER BY account",
    )
    assert query.returncode == 0, query.stderr
    assert "Assets:B银行:C储蓄" in query.stdout

    result = _bea(tmp_path, "treeify", stdin=query.stdout)

    assert result.returncode == 0, result.stderr
    assert "Assets:" not in result.stdout
    assert "Expenses:" not in result.stdout
    names = re.findall(r"[|`]-- (\S+)", result.stdout)
    assert names == ["Assets", "B银行", "Checking", "C储蓄", "Equity", "Opening", "Expenses", "F餐饮", "L午餐"]


def test_every_account_non_ascii_is_a_tree_not_a_refusal(tmp_path: Path) -> None:
    result = _bea(tmp_path, "treeify", stdin="Assets:Épargne:Livret  1\nAssets:Épargne:Élan    2\n")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "`-- Assets\n    `-- Épargne\n        |-- Livret     1\n        `-- Élan       2\n"


@pytest.mark.parametrize("preset", ["-A", "-F"])
def test_an_explicit_preset_is_still_upstreams(tmp_path: Path, preset: str) -> None:
    """`-A`/`-F` conflict with a pattern upstream; bea must not add one beside them."""
    result = _bea(tmp_path, "treeify", preset, stdin="src/cli/a.py  1\nsrc/cli/b.py  2\nlib:x:y  3\nlib:x:z  4\n")

    assert result.returncode == 0, result.stderr
    assert "Conflicted pattern options" not in result.stderr
    assert "`-- " in result.stdout
