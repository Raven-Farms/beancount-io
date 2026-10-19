"""A stored query with an empty window is skipped by name, not a full stop (w5/746).

`.run *` stopped at the first stored query whose directive date closed its
window: exit 2, empty stdout, the refusal naming no query, every other answer
lost. And a stored `OPEN ON … CLOSE` was told to drop CLOSE because the window
"already runs to the end of the ledger" — but a stored query's open window
closes at its directive date, so the advice dropped rows.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENTRIES = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash
2026-01-01 open Expenses:Food
2026-01-01 open Equity:Opening
2026-01-02 txn "Opening"
  Assets:Cash 100.00 USD
  Equity:Opening
2026-01-10 txn "Lunch"
  Expenses:Food 10.00 USD
  Assets:Cash
2026-01-20 txn "Dinner"
  Expenses:Food 20.00 USD
  Assets:Cash
"""

SQ3 = (
    ENTRIES
    + """2026-01-15 query "a-ok" "SELECT date, narration WHERE account = 'Expenses:Food'"
2026-01-15 query "b-zero" "SELECT date, narration FROM OPEN ON 2026-01-15 WHERE account = 'Expenses:Food'"
2026-01-15 query "c-ok" "SELECT date, narration FROM OPEN ON 2026-01-05 WHERE account = 'Expenses:Food'"
"""
)

BC = (
    ENTRIES
    + '2026-01-15 query "food-bare" '
    + "\"SELECT date, narration FROM OPEN ON 2026-01-05 CLOSE WHERE account = 'Expenses:Food'\"\n"
    + '2026-01-15 query "food-open" '
    + "\"SELECT date, narration FROM OPEN ON 2026-01-05 WHERE account = 'Expenses:Food'\"\n"
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
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
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _ledger(tmp_path: Path, text: str) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(text, encoding="utf-8")
    return ledger


def test_run_star_skips_the_empty_window_by_name_and_answers_the_rest(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, SQ3)

    result = _bea(tmp_path, "--file", str(ledger), "query", ".run *")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "a-ok:" in result.stdout and "c-ok:" in result.stdout, result.stdout
    assert "Lunch" in result.stdout, result.stdout
    assert "b-zero:" not in result.stdout, "a skipped query leaves no header behind"
    assert '"b-zero"' in result.stderr, result.stderr
    assert "Skipped" in result.stderr, result.stderr


def test_run_name_refuses_the_empty_window_by_name(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, SQ3)

    text = _bea(tmp_path, "--file", str(ledger), "query", ".run b-zero")
    as_json = _bea(tmp_path, "--json", "--file", str(ledger), "query", ".run b-zero")

    assert text.returncode == 2, text.stdout + text.stderr
    assert '"b-zero"' in text.stderr, text.stderr
    assert "covers no days" in text.stderr
    error = json.loads(as_json.stderr)["error"]
    assert (error["exit_code"], error["category"]) == (2, "usage")
    assert '"b-zero"' in error["message"], error


def test_a_bare_close_in_a_stored_query_names_the_directive_date(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, BC)

    refused = _bea(tmp_path, "--file", str(ledger), "query", ".run food-bare")

    assert refused.returncode == 2, refused.stdout + refused.stderr
    assert '"food-bare"' in refused.stderr, refused.stderr
    assert "2026-01-15" in refused.stderr, "the date the window actually closes at"
    assert "end of the ledger" not in refused.stderr, refused.stderr
    assert "CLOSE ON" in refused.stderr, refused.stderr

    kept = _bea(
        tmp_path,
        "--file",
        str(ledger),
        "query",
        "SELECT date, narration FROM OPEN ON 2026-01-05 CLOSE ON 2026-01-21 WHERE account = 'Expenses:Food'",
    )

    assert kept.returncode == 0, kept.stderr
    assert "Dinner" in kept.stdout, "the advised CLOSE ON keeps what dropping CLOSE lost"
