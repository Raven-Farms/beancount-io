"""`query --source memory:` is refused like any other unusable scheme (w5/288).

The scheme allow-list exists so a source upstream cannot attach never reaches
a traceback, but it listed `memory`, whose upstream module has no `attach`:
`--source memory:` exited 1 with an AttributeError traceback, and the refusal
for a mistyped scheme recommended `memory:...`. The list now holds only the
schemes that answer, and the hint is built from it.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.query_terminal import QueryTerminal

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Equity:Opening USD
2024-01-02 * "Open"
  Assets:Cash  100.00 USD
  Equity:Opening
"""
PREVIOUS = b"account\nAssets:Cash\n"


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "report.csv").write_bytes(PREVIOUS)
    return tmp_path


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        XDG_DATA_HOME=str(books / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _hinted_schemes(stderr: str) -> list[str]:
    return re.findall(r"(\w+):\.\.\.", stderr.replace("\n", " "))


@pytest.mark.parametrize("source", ["memory:", "memory:table", "MEMORY:"])
def test_memory_source_exits_2_with_one_line(books: Path, source: str) -> None:
    result = _bea(books, "query", "--source", source, "SELECT 1", "-f", "csv", "-o", "report.csv")

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"--source scheme '{source.partition(':')[0]}' is not supported" in result.stderr.replace("\n", " ")
    assert "Traceback" not in result.stderr
    assert "AttributeError" not in result.stderr
    assert len(result.stderr.strip().splitlines()) <= 2  # one sentence, wrapped at most once
    assert result.stdout == ""
    assert (books / "report.csv").read_bytes() == PREVIOUS


def test_bad_scheme_hint_names_only_schemes_that_answer(books: Path) -> None:
    result = _bea(books, "query", "--source", "bean:main.bean", "SELECT 1")

    assert result.returncode == 2, result.stdout + result.stderr
    hinted = _hinted_schemes(result.stderr)
    assert hinted == ["beancount", "csv", "test"]
    assert "bare path" in result.stderr.replace("\n", " ")

    # Every scheme the hint offers attaches and answers.
    (books / "t.csv").write_text("a,b\n1,2\n")
    working = {
        "beancount": ("beancount:main.bean", "SELECT account FROM accounts ORDER BY account LIMIT 1", "Assets:Cash"),
        "csv": ("csv:t.csv", "SELECT a FROM t", "1"),
        "test": ("test:", "SELECT 1 AS one", "1"),
    }
    for scheme in hinted:
        source, query, cell = working[scheme]
        answer = _bea(books, "query", "--source", source, query)
        assert answer.returncode == 0, f"{scheme}: {answer.stderr}"
        assert cell in answer.stdout.split(), f"{scheme}: {answer.stdout}"


def test_interactive_memory_source_never_opens_a_prompt(books: Path) -> None:
    with QueryTerminal(books, ["query", "--source", "memory:"]) as shell:
        screen = shell.read()
        assert shell.process.wait(timeout=10) == 2
    assert "scheme 'memory' is not supported" in screen.replace("\n", " ")
    assert "Traceback" not in screen
    assert "beanquery>" not in screen
