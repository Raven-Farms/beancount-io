"""A stored `query` directive with no BQL is refused by name, and `.run *` goes on (w5/276).

A placeholder `query "empty" ""` handed the parser an empty string, which
raised a bare `IndexError`: `.run empty` exited 1 with no mention of the
directive, and `.run *` answered none of the ledger's other stored queries.
The `--source` one-shot and both shells printed the traceback. A stored body
that is blank or only comments is now a usage error naming the query, and
`.run *` skips it with a stderr line and still answers the rest.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.query_terminal import QueryTerminal

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """2026-01-01 open Assets:A USD
2026-01-01 open Expenses:F USD
2026-01-02 * "x"
  Expenses:F  1 USD
  Assets:A
2026-01-03 query "one" "SELECT account, sum(number) AS s GROUP BY account"
2026-01-05 query "empty" ""
2026-01-06 query "blank" "   "
2026-01-07 query "remark" "/* later */"
2026-01-08 query "two" "SELECT count(*) AS postings"
"""
TRACEBACK = "Traceback (most recent call last)"

SURFACES = pytest.mark.parametrize("native", [False, True], ids=["file", "source"])


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "stored.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def _args(ledger: Path, native: bool) -> list[str]:
    return ["query", "--source", str(ledger)] if native else ["--file", str(ledger), "query"]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
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
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


@SURFACES
@pytest.mark.parametrize("name", ["empty", "blank", "remark"])
def test_run_of_an_empty_stored_query_is_a_usage_error_naming_it(
    tmp_path: Path, ledger: Path, native: bool, name: str
) -> None:
    result = _bea(tmp_path, *_args(ledger, native), f".run {name}")

    assert result.returncode == 2, result.stderr
    assert f'stored query "{name}" has an empty body' in result.stderr
    assert "IndexError" not in result.stderr
    assert TRACEBACK not in result.stderr
    assert result.stdout == ""


def test_run_of_an_empty_stored_query_is_a_json_usage_error(tmp_path: Path, ledger: Path) -> None:
    result = _bea(tmp_path, "--json", "--file", str(ledger), "query", ".run empty")

    assert result.returncode == 2, result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert error["message"] == 'stored query "empty" has an empty body.'
    assert result.stdout == ""


@SURFACES
def test_run_all_answers_the_other_stored_queries_and_reports_the_empty_ones(
    tmp_path: Path, ledger: Path, native: bool
) -> None:
    result = _bea(tmp_path, *_args(ledger, native), ".run *")

    assert result.returncode == 0, result.stderr
    assert "one:" in result.stdout
    assert "Expenses:F" in result.stdout
    assert "two:" in result.stdout
    for name in ("empty", "blank", "remark"):
        assert f'Skipped stored query "{name}": its body is empty.' in result.stderr
        assert f"{name}:" not in result.stdout
    assert TRACEBACK not in result.stderr


@SURFACES
def test_a_stored_query_with_bql_still_runs(tmp_path: Path, ledger: Path, native: bool) -> None:
    result = _bea(tmp_path, *_args(ledger, native), ".run one")

    assert result.returncode == 0, result.stderr
    assert "Expenses:F" in result.stdout
    assert "empty body" not in result.stderr


@SURFACES
def test_the_prompt_explains_an_empty_stored_query_and_stays_usable(tmp_path: Path, ledger: Path, native: bool) -> None:
    with QueryTerminal(tmp_path, _args(ledger, native)) as shell:
        shell.read("beanquery>")

        shell.send(".run empty")
        reply = shell.read("beanquery>")
        assert 'stored query "empty" has an empty body.' in reply
        assert TRACEBACK not in reply
        assert "IndexError" not in reply

        shell.send(".run *")
        everything = shell.read("beanquery>")
        assert "Expenses:F" in everything
        assert 'Skipped stored query "empty": its body is empty.' in everything

        shell.send(".run two")
        answer = shell.read("beanquery>").splitlines()
        assert answer[-2].strip() == "2", "the session keeps answering afterwards"
        assert shell.finish() == 0
