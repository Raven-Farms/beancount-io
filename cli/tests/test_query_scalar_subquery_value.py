"""A subquery used as a single value is a usage error, not a ledger failure (w5/180).

Beanquery has no scalar subqueries. The SELECT-list form already exited 2 with
guidance; comparing, negating or computing with one escaped as
`AttributeError: 'EvalQuery' object has no attribute 'dtype'` and exit 1, the
status reserved for a ledger that fails validation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
2024-01-01 open Assets:Cash
2024-01-01 open Expenses:Food

2024-01-05 * "Grocer" "Food"
  Expenses:Food  10.00 USD
  Assets:Cash

2024-01-06 * "No payee"
  Expenses:Food  5.00 USD
  Assets:Cash
"""
GUIDANCE = "Filter with it instead: SELECT ... WHERE column IN (SELECT ...)"

SCALAR_USES = {
    "where-comparison": "SELECT account, count(*) WHERE date > (SELECT min(date) FROM #entries) GROUP BY account",
    "where-arithmetic": "SELECT account WHERE number + (SELECT 1) > 2",
    "where-negation": "SELECT account WHERE NOT (SELECT 1)",
    "where-conjunction": "SELECT account WHERE date > 2024-01-01 AND (SELECT 1)",
    "having-comparison": "SELECT account, count(*) GROUP BY account HAVING count(*) > (SELECT 1)",
    "function-argument": "SELECT length((SELECT 1))",
}


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("query", SCALAR_USES.values(), ids=SCALAR_USES.keys())
def test_a_subquery_used_as_a_value_is_a_usage_error(tmp_path: Path, query: str) -> None:
    result = _bea(tmp_path, "-f", "main.bean", "query", query)

    assert result.returncode == 2, result.stderr
    assert "BQL cannot use a subquery as a single value." in result.stderr
    assert GUIDANCE in result.stderr
    assert "EvalQuery" not in result.stderr
    assert "--debug" not in result.stderr
    assert result.stdout == ""


def test_the_json_envelope_classifies_it_as_usage(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json", "-f", "main.bean", "query", SCALAR_USES["where-comparison"])

    assert result.returncode == 2, result.stderr
    error = json.loads(result.stdout or result.stderr)["error"]
    assert error["category"] == "usage"
    assert "subquery" in error["message"]
    assert "EvalQuery" not in json.dumps(error)


def test_the_select_list_form_keeps_its_own_message(tmp_path: Path) -> None:
    result = _bea(tmp_path, "-f", "main.bean", "query", "SELECT date, (SELECT max(date) FROM #prices) AS d")

    assert result.returncode == 2, result.stderr
    assert "BQL cannot use a subquery in the SELECT list." in result.stderr
    assert GUIDANCE in result.stderr


def test_the_in_form_the_guidance_names_still_runs(tmp_path: Path) -> None:
    query = "SELECT account, count(*) AS n WHERE date IN (SELECT max(date) FROM #entries) GROUP BY account"
    result = _bea(tmp_path, "--json", "-f", "main.bean", "query", query)

    assert result.returncode == 0, result.stderr
    assert sorted(json.loads(result.stdout)["data"]["rows"]) == [["Assets:Cash", 1], ["Expenses:Food", 1]]
