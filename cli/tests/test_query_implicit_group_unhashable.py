"""An unhashable column beside an aggregate with no GROUP BY is a usage error (w5/260)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
QUERY = "SELECT other_accounts, count(*)"
LEDGER = f"""2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-02 * "Shop" "x" #trip
  Expenses:Food 5 USD
  Assets:Cash
2024-01-03 query "per-counterparty" "{QUERY}"
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
        stdin=subprocess.DEVNULL,
    )


def _ledger(tmp_path: Path) -> str:
    ledger = tmp_path / "m.bean"
    ledger.write_text(LEDGER)
    return str(ledger)


@pytest.mark.parametrize(
    ("query", "column", "kind", "recipe"),
    [
        (QUERY, "other_accounts", "list", "joinstr(other_accounts)"),
        ("SELECT count(*), other_accounts, sum(number)", "other_accounts", "list", "joinstr(other_accounts)"),
        ("SELECT balance, sum(number)", "balance", "Inventory", "str(balance)"),
        ("SELECT meta, count(*)", "meta", "dict", "str(meta)"),
        ("SELECT accounts, count(*) FROM transactions", "accounts", "set", "without the aggregate"),
    ],
)
def test_the_implicit_form_is_a_usage_error_naming_the_column(
    tmp_path: Path, query: str, column: str, kind: str, recipe: str
) -> None:
    result = _bea(tmp_path, "--file", _ledger(tmp_path), "query", query)
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    first = result.stderr.splitlines()[0]
    assert first == f"Error: Cannot run this BQL query: BQL cannot group by {column} ({kind}), which it cannot hash."
    assert recipe in result.stderr
    assert "TypeError" not in result.stderr
    assert "--debug" not in result.stderr


def test_every_unhashable_column_is_named_and_the_hashable_one_is_not(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--file", _ledger(tmp_path), "query", "SELECT other_accounts, meta, account, count(*)")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "cannot group by other_accounts (list), meta (dict), which" in result.stderr.splitlines()[0]


def test_json_callers_get_a_usage_error_not_a_validation_failure(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json", "--file", _ledger(tmp_path), "query", QUERY)
    assert result.returncode == 2, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert "other_accounts" in error["message"]
    assert any("joinstr(other_accounts)" in detail for detail in error["details"])


def test_a_stored_query_and_the_native_source_explain_it_the_same_way(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    for args in (["--file", ledger, "query", ".run per-counterparty"], ["query", "--source", ledger, QUERY]):
        result = _bea(tmp_path, *args)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "cannot group by other_accounts (list)" in result.stderr
        assert "Traceback" not in result.stderr
        assert "TypeError" not in result.stderr


def test_the_recipe_it_names_runs(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        "--json",
        "--file",
        _ledger(tmp_path),
        "query",
        "SELECT joinstr(other_accounts), count(*) GROUP BY joinstr(other_accounts)",
    )
    assert result.returncode == 0, result.stderr
    assert sorted(json.loads(result.stdout)["data"]["rows"]) == [["Assets:Cash", 1], ["Expenses:Food", 1]]


def test_the_explicit_group_by_control_is_unchanged(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--file", _ledger(tmp_path), "query", f"{QUERY} GROUP BY other_accounts")
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stderr.splitlines()[0] == (
        "Error: Cannot run this BQL query: GROUP-BY a non-hashable type is not supported: "
        "\"Column(name='other_accounts')\"."
    )


def test_hashable_columns_beside_an_aggregate_still_group(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    by_account = _bea(tmp_path, "--json", "--file", ledger, "query", "SELECT account, count(*)")
    assert by_account.returncode == 0, by_account.stderr
    assert sorted(json.loads(by_account.stdout)["data"]["rows"]) == [["Assets:Cash", 1], ["Expenses:Food", 1]]
    # A frozenset hashes, so `tags` was never part of this failure.
    by_tags = _bea(tmp_path, "--json", "--file", ledger, "query", "SELECT tags, count(*)")
    assert by_tags.returncode == 0, by_tags.stderr
    assert json.loads(by_tags.stdout)["data"]["rows"] == [[["trip"], 2]]
