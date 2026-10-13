"""`FROM OPEN ON <date> CLOSE` is a usage error, and GROUP BY never masks one (w5/177).

Beanquery orders a dated `OPEN` against the `True` a bare `CLOSE` parses to,
so the query escaped as a raw `TypeError` classified as a ledger failure
(exit 1). With `GROUP BY 1` or `GROUP BY root(account, 1)` the handler that
explains TypeErrors read `.name` off an int or a function node, and its own
`AttributeError` replaced whatever had really gone wrong.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

BARE_CLOSE = "SELECT account, sum(number) FROM OPEN ON 2024-01-01 CLOSE GROUP BY account"

LEDGER = f"""2024-01-01 open Assets:Cash
2024-01-01 open Expenses:Food

2024-01-05 * "Grocer" "Food"
  Expenses:Food  10.00 USD
  Assets:Cash

2024-01-06 * "No payee"
  Expenses:Food  5.00 USD
  Assets:Cash

2024-01-10 query "bare-close" "{BARE_CLOSE}"
"""

TOTALS = [["Expenses:Food", "15.00"], ["Assets:Cash", "-15.00"]]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        HOME=str(tmp_path / "home"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args[:-1], "--file", str(ledger), "query", args[-1]],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize(
    "query",
    [
        BARE_CLOSE,
        "SELECT account, sum(number) FROM OPEN ON 2024-01-01 CLOSE GROUP BY 1",
        "SELECT root(account, 1), sum(number) FROM OPEN ON 2024-01-01 CLOSE GROUP BY root(account, 1)",
        "BALANCES FROM OPEN ON 2024-01-01 CLOSE",
        "JOURNAL FROM OPEN ON 2024-01-01 CLOSE",
        "SELECT account FROM #accounts WHERE account IN (SELECT account FROM OPEN ON 2024-01-01 CLOSE)",
        ".run bare-close",
    ],
    ids=["group-by-name", "group-by-index", "group-by-function", "balances", "journal", "subquery", "stored"],
)
def test_a_dated_open_with_a_bare_close_is_a_usage_error_naming_close(tmp_path: Path, query: str) -> None:
    result = _bea(tmp_path, query)

    assert result.returncode == 2, result.stderr
    assert "OPEN ON 2024-01-01 with a bare CLOSE" in result.stderr
    assert "CLOSE ON YYYY-MM-DD" in result.stderr
    assert "TypeError" not in result.stderr
    assert "AttributeError" not in result.stderr


def test_the_refusal_reaches_json_callers_as_usage(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json", BARE_CLOSE.replace("GROUP BY account", "GROUP BY 1"))

    assert result.returncode == 2
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert "bare CLOSE" in error["message"]
    assert any("drop CLOSE" in detail for detail in error["details"])


@pytest.mark.parametrize(
    "from_clause",
    ["FROM OPEN ON 2024-01-01 CLOSE ON 2025-01-01", "FROM OPEN ON 2024-01-01", "FROM CLOSE"],
    ids=["dated-close", "open-only", "close-only"],
)
def test_the_windows_beanquery_can_compile_still_answer(tmp_path: Path, from_clause: str) -> None:
    """The control: only a dated OPEN beside a bare CLOSE is refused."""
    result = _bea(tmp_path, "--json", f"SELECT account, sum(number) {from_clause} GROUP BY 1")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["rows"] == TOTALS


def test_a_function_in_group_by_does_not_hide_the_set_column_advice(tmp_path: Path) -> None:
    """Another upstream TypeError the handler explains, once it can read the clause."""
    result = _bea(tmp_path, "SELECT root(account, 1), accounts, count(*) GROUP BY root(account, 1), accounts")

    assert result.returncode == 2, result.stderr
    assert "GROUP BY on accounts" in result.stderr
    assert "has no attribute 'name'" not in result.stderr


def test_a_positional_group_by_reports_the_real_error(tmp_path: Path) -> None:
    """Unexplained failures still propagate, as themselves rather than as the handler's."""
    result = _bea(tmp_path, "SELECT accounts, count(*) GROUP BY 1")

    assert result.returncode != 0
    assert "has no attribute 'name'" not in result.stderr
    assert "AttributeError" not in result.stderr
