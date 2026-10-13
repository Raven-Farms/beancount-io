"""`.run` takes a stored query's name exactly as `.run` lists it (w5/237).

A stored query named `this month's food` is listed by a bare `.run`, but
running it by that name split the argument as a shell line, and the apostrophe
escaped as `ValueError: No closing quotation` — exit 1 one-shot, a Python
traceback at the prompt. The whole argument is now tried as a name first, and
an argument that is neither a name nor a readable quoted form is a usage
error naming the stored queries.
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
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Cafe" "Coffee"
  Expenses:Food  4.00 USD
  Assets:Cash
2026-02-05 * "Cafe" "Tea"
  Expenses:Food  3.00 USD
  Assets:Cash
2026-01-01 query "this month's food" "SELECT sum(position) AS total WHERE account ~ 'Food'"
2026-01-01 query "plain" "SELECT count(*) AS n"
"""
NAME = "this month's food"
UNREADABLE = 'cannot read the "run" query name: No closing quotation.'
STORED = "Stored queries in this ledger: plain, this month's food."

SHELLS = pytest.mark.parametrize("native", [False, True], ids=["file", "source"])


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def _query_args(ledger: Path, native: bool) -> list[str]:
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


@SHELLS
@pytest.mark.parametrize("argument", [NAME, NAME + ";", f'"{NAME}"'], ids=["listed", "semicolon", "quoted"])
def test_a_name_with_an_apostrophe_runs_as_listed(tmp_path: Path, ledger: Path, native: bool, argument: str) -> None:
    listed = _bea(tmp_path, *_query_args(ledger, native), ".run")
    assert listed.returncode == 0, listed.stderr
    assert NAME in listed.stdout.splitlines()

    result = _bea(tmp_path, *_query_args(ledger, native), f".run {argument}")
    assert result.returncode == 0, result.stderr
    assert "7.00 USD" in result.stdout
    assert "ValueError" not in result.stderr


@SHELLS
def test_an_unreadable_argument_is_a_usage_error(tmp_path: Path, ledger: Path, native: bool) -> None:
    human = _bea(tmp_path, *_query_args(ledger, native), ".run nobody's query")
    assert human.returncode == 2, human.stderr
    assert UNREADABLE in human.stderr
    assert '.run "it\'s mine"' in human.stderr
    assert STORED in human.stderr
    assert "ValueError" not in human.stderr
    assert human.stdout == ""

    if native:
        return  # `--json` requires a local `--file`.
    as_json = _bea(tmp_path, "--json", *_query_args(ledger, native), ".run nobody's query")
    assert as_json.returncode == 2, as_json.stderr
    error = json.loads(as_json.stderr)["error"]
    assert error["category"] == "usage"
    assert error["message"] == UNREADABLE


@SHELLS
def test_the_other_run_refusals_are_unchanged(tmp_path: Path, ledger: Path, native: bool) -> None:
    missing = _bea(tmp_path, *_query_args(ledger, native), ".run nope")
    assert missing.returncode == 2, missing.stderr
    assert 'query "nope" not found.' in missing.stderr
    assert STORED in missing.stderr

    extra = _bea(tmp_path, *_query_args(ledger, native), ".run plain extra")
    assert extra.returncode == 2, extra.stderr
    assert 'too many arguments for "run" command' in extra.stderr

    quoted = _bea(tmp_path, *_query_args(ledger, native), ".run 'plain'")
    assert quoted.returncode == 0, quoted.stderr
    assert "4" in quoted.stdout.split()


@SHELLS
def test_the_prompt_runs_the_name_and_explains_the_mistake(tmp_path: Path, ledger: Path, native: bool) -> None:
    with QueryTerminal(tmp_path, _query_args(ledger, native)) as shell:
        shell.read("beanquery>")

        shell.send(f".run {NAME}")
        assert "7.00 USD" in shell.read("beanquery>")

        shell.send(".run nobody's query")
        reply = shell.read("beanquery>")
        assert UNREADABLE in reply
        assert STORED in reply

        shell.send(".run plain")
        assert "\n4\n" in shell.read("beanquery>"), "the session keeps answering afterwards"
        assert shell.finish() == 0
        assert "ValueError" not in shell.screen
        assert "Traceback (most recent call last)" not in shell.screen
    assert ledger.read_text(encoding="utf-8") == LEDGER
