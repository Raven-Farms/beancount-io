"""`query --source` reports an upstream failure in one line, the stack only under `--debug` (w5/472).

Upstream's display context holds an amount to twelve integer digits, so a
10^12 VND balance raised `InvalidOperation` and printed a 200-line boxed
traceback with exit 1, where `--file` answers. A NaN did the same with a
`TypeError`, and the `--source` prompt printed the raw stack.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.query_terminal import QueryTerminal

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "VND"
2026-01-01 open Assets:Bank VND
2026-01-01 open Equity:Opening VND
2026-01-02 * "Opening"
  Assets:Bank  1000000000000 VND
  Equity:Opening
"""
HINT = "Pass --debug before the command for a traceback."
GROUPED = "SELECT account, sum(position) GROUP BY account"


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    return path


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_a_trillion_unit_balance_fails_in_one_line(ledger: Path) -> None:
    result = _bea(ledger.parent, "query", "--source", str(ledger), GROUPED)

    assert result.returncode == 1
    lines = result.stderr.strip().splitlines()
    assert len(lines) == 1, result.stderr
    assert lines[0].startswith("error: Decimal arithmetic failed while running or printing this query")
    assert "--file" in lines[0] and lines[0].endswith(HINT)
    assert "Traceback" not in result.stderr and "╭" not in result.stderr

    answered = _bea(ledger.parent, "-f", str(ledger), "query", GROUPED)
    assert answered.returncode == 0, answered.stderr
    assert "1000000000000 VND" in answered.stdout


def test_any_other_upstream_exception_fails_in_one_line(ledger: Path) -> None:
    result = _bea(ledger.parent, "query", "--source", str(ledger), "SELECT decimal('NaN')")

    assert result.returncode == 1
    assert result.stderr.strip().splitlines() == [
        f"error: TypeError: '>' not supported between instances of 'str' and 'int'. {HINT}"
    ]


def test_debug_shows_the_stack(ledger: Path) -> None:
    result = _bea(ledger.parent, "--debug", "query", "--source", str(ledger), GROUPED)

    assert result.returncode == 1
    assert "Traceback (most recent call last)" in result.stderr
    assert result.stderr.rstrip().splitlines()[-1].startswith("error: Decimal arithmetic failed")
    assert HINT not in result.stderr


def test_the_source_prompt_reports_it_and_carries_on(ledger: Path) -> None:
    with QueryTerminal(ledger.parent, ["query", "--source", str(ledger)]) as shell:
        shell.read("beanquery>")
        shell.send(GROUPED)
        reply = shell.read("beanquery>")
        assert "error: Decimal arithmetic failed while running or printing this query" in reply
        assert "Traceback" not in reply

        shell.send("SELECT 1 + 1 AS two")
        assert "2" in shell.read("beanquery>")
        shell.send(".quit")
        assert shell.finish() == 0
