"""Native query sources refuse load caches that could destroy the books (w5/670)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.query_terminal import ROOT, QueryTerminal

MAIN = 'include "txns/*.bean"\n2024-01-01 open Assets:Cash USD\n'
CHILD = """2024-01-01 open Equity:Opening USD
2024-01-02 * "Opening"
  Assets:Cash 73 USD
  Equity:Opening
"""
QUERY = "SELECT 73 AS n LIMIT 1"
CACHE_TARGETS = ["main.bean", "{filename}", "txns/a.bean", "txns/q.bean"]


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "txns").mkdir()
    root = tmp_path / "main.bean"
    root.write_text(MAIN)
    (tmp_path / "txns/a.bean").write_text(CHILD)
    return root


def _ledger_bytes(directory: Path) -> dict[str, bytes]:
    return {str(path.relative_to(directory)): path.read_bytes() for path in directory.rglob("*.bean")}


def _environment(directory: Path, pattern: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("BEA_")}
    env.update(
        BEANCOUNT_LOAD_CACHE_FILENAME=pattern,
        BEA_CONFIG_DIR=str(directory / "config"),
        BEA_ENGINE_DIR=str(directory / "engine"),
        BEA_NO_UPDATE_NOTIFIER="1",
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
        CI="",
    )
    return env


def _run(directory: Path, pattern: str, module: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=directory,
        env=_environment(directory, pattern),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _assert_refusal(screen: str, pattern: str) -> None:
    assert "BEANCOUNT_LOAD_CACHE_FILENAME" in screen
    assert pattern in screen
    assert "Nothing was changed." in screen
    assert "Traceback" not in screen
    if pattern == "txns/q.bean":
        assert "txns/*.bean" in screen
        assert "once the cache is written" in screen
    else:
        assert "would delete the ledger" in screen


@pytest.mark.parametrize("pattern", CACHE_TARGETS, ids=["root", "filename-pattern", "include", "new-include"])
@pytest.mark.parametrize("source", ["main.bean", "beancount:main.bean"], ids=["path", "uri"])
@pytest.mark.parametrize("interactive", [False, True], ids=["one-shot", "terminal"])
def test_source_refuses_a_cache_inside_the_ledger(
    tmp_path: Path, books: Path, pattern: str, source: str, interactive: bool
) -> None:
    before = _ledger_bytes(tmp_path)
    args = ["query", "--source", source]
    if interactive:
        with QueryTerminal(tmp_path, args, env={"BEANCOUNT_LOAD_CACHE_FILENAME": pattern}) as terminal:
            # Baseline opens a prompt; queue an exit so a failed guard never
            # leaves this regression test waiting for interactive input.
            terminal.send(".exit")
            screen = terminal.read()
            status = terminal.process.wait(timeout=10)
        assert "beanquery>" not in screen, screen
    else:
        result = _run(tmp_path, pattern, "cli.main", "--no-input", *args, QUERY)
        screen = result.stdout + result.stderr
        status = result.returncode
        assert result.stdout == "", screen

    assert status == 2, screen
    _assert_refusal(screen, pattern)
    assert _ledger_bytes(tmp_path) == before
    assert books.exists()


@pytest.mark.parametrize("pattern", CACHE_TARGETS, ids=["root", "filename-pattern", "include", "new-include"])
def test_engine_source_query_refuses_without_the_frontend(tmp_path: Path, books: Path, pattern: str) -> None:
    before = _ledger_bytes(tmp_path)
    result = _run(tmp_path, pattern, "bea_engine", "source-query", "beancount:main.bean", QUERY)

    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    _assert_refusal(result.stderr, pattern)
    assert _ledger_bytes(tmp_path) == before
    assert books.exists()


@pytest.mark.parametrize("source", ["main.bean", "beancount:main.bean"], ids=["path", "uri"])
def test_source_accepts_a_cache_outside_the_books(tmp_path: Path, books: Path, source: str) -> None:
    before = _ledger_bytes(tmp_path)
    result = _run(tmp_path, "safe-cache.pickle", "cli.main", "--no-input", "query", "--source", source, QUERY)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "73" in result.stdout.split()
    assert "BEANCOUNT_LOAD_CACHE_FILENAME" not in result.stderr
    assert _ledger_bytes(tmp_path) == before
    assert books.exists()


@pytest.mark.parametrize(
    ("source", "query"),
    [("csv:t.csv", "SELECT n FROM t"), ("test:", "SELECT 73 AS n FROM test LIMIT 1")],
    ids=["csv", "test"],
)
def test_non_beancount_sources_ignore_the_beancount_cache(tmp_path: Path, books: Path, source: str, query: str) -> None:
    (tmp_path / "t.csv").write_text("n\n73\n")
    before = _ledger_bytes(tmp_path)
    result = _run(tmp_path, "main.bean", "cli.main", "--no-input", "query", "--source", source, query)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "73" in result.stdout.split()
    assert "BEANCOUNT_LOAD_CACHE_FILENAME" not in result.stderr
    assert _ledger_bytes(tmp_path) == before
    assert books.exists()


def test_native_shell_rechecks_the_cache_before_a_reload(tmp_path: Path, books: Path) -> None:
    before = _ledger_bytes(tmp_path)
    # Keep upstream's process-global loader cache configuration in a child.
    # Changing the environment after construction specifically exercises the
    # reload guard rather than another constructor-time check.
    script = """import os
import sys
from bea_engine import protocol
from bea_engine.query import _native_shell

shell = _native_shell("main.bean", interactive=False, format="text", numberify=False, show_errors=False)
os.environ["BEANCOUNT_LOAD_CACHE_FILENAME"] = "txns/a.bean"
try:
    shell.do_reload()
except protocol.UsageError as exc:
    print(str(exc), file=sys.stderr)
    raise SystemExit(2)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=_environment(tmp_path, "safe-cache.pickle"),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    _assert_refusal(result.stderr, "txns/a.bean")
    assert _ledger_bytes(tmp_path) == before
    assert books.exists()
