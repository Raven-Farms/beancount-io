"""Mixed-type ORDER BY answers, and set columns refuse with fitting advice (w5/760).

`ORDER BY` over metadata mixing text and numbers died with a bare
TypeError; DISTINCT over a subquery's set column got the tags recipes for
an `other_accounts` column; `joinstr(accounts)` died with a bare
AttributeError; and `DISTINCT meta` leaked an unhashable-dict TypeError.
Mixed keys now sort by their text, aliases report their underlying column,
functions over sets are refused as such, and DISTINCT names its column.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2020-01-01 open Assets:Cash USD
2020-01-01 open Expenses:Food

2020-01-05 * "a"
  ref: "A-12"
  Assets:Cash  1 USD
  Expenses:Food

2020-01-06 * "b"
  ref: 5
  Assets:Cash  2 USD
  Expenses:Food
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
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
        timeout=60,
    )


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "q.bean"
    ledger.write_text(LEDGER)
    return ledger


def _query(tmp_path: Path, statement: str) -> subprocess.CompletedProcess[str]:
    return _bea(tmp_path, "--file", str(_ledger(tmp_path)), "query", statement)


def test_order_by_mixed_meta_answers_in_text_order(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT date, entry_meta('ref') AS ref ORDER BY ref")
    assert result.returncode == 0, result.stderr
    assert "TypeError" not in result.stdout + result.stderr
    # The ORDER BY str(...) control's order: '5' sorts before 'A-12'.
    assert result.stdout.index("5") < result.stdout.index("A-12")


def test_order_by_a_mapping_answers(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT date ORDER BY meta LIMIT 1")
    assert result.returncode == 0, result.stderr
    assert "TypeError" not in result.stdout + result.stderr


def test_distinct_over_subquery_list_names_the_list(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT DISTINCT o FROM (SELECT other_accounts AS o)")
    assert result.returncode == 2, result.stdout
    assert "cannot use DISTINCT or GROUP BY on other_accounts" in result.stderr
    assert "joinstr(other_accounts)" in result.stderr
    assert "starred expression" not in result.stderr
    assert "joinstr(tags)" not in result.stderr


def test_function_over_accounts_is_refused_as_such(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT joinstr(accounts), count(*) GROUP BY joinstr(accounts)")
    assert result.returncode == 2, result.stdout
    assert "BQL cannot apply joinstr to accounts" in result.stderr
    assert "__mro__" not in result.stderr
    assert "AttributeError" not in result.stderr


def test_str_over_accounts_is_refused_as_such(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT str(accounts) FROM entries LIMIT 1")
    assert result.returncode == 2, result.stdout
    assert "BQL cannot apply str to accounts" in result.stderr


def test_group_by_accounts_gets_accounts_advice(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT accounts, count(*) GROUP BY accounts")
    assert result.returncode == 2, result.stdout
    assert "cannot use DISTINCT or GROUP BY on accounts" in result.stderr
    assert "no BQL function reads a set" in result.stderr
    assert "joinstr(tags)" not in result.stderr


def test_distinct_meta_names_the_column_and_recipe(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT DISTINCT meta FROM entries")
    assert result.returncode == 2, result.stdout
    assert "BQL cannot use DISTINCT on meta (dict)" in result.stderr
    assert "SELECT DISTINCT str(meta)" in result.stderr
    assert "unhashable" not in result.stderr
    assert "ImmutableDict" not in result.stderr


def test_distinct_meta_recipe_runs(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT DISTINCT str(meta) FROM entries")
    assert result.returncode == 0, result.stderr
