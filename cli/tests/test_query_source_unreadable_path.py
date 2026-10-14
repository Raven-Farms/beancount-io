"""Native `query --source` names a path it cannot open in one line (w5/250).

Upstream opens what `--source` names with no guard of its own, so a `csv:`
path that is missing or a directory, a source with no path at all (`--source
""` from an unset shell variable) and a file the user may not read each ended
in a boxed traceback through bea's engine files, without `--debug`. `--file`
with the same directory is a one-line usage error. The frontend now refuses
those before the engine starts, the engine refuses them for someone running the
helper directly, and an I/O failure it could not foresee is one line too.
w5/249 covers the Beancount ledger that is missing or a directory.
"""

from __future__ import annotations

import os
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
2024-01-03 * "Lunch"
  Expenses:Food  12.50 USD
  Assets:Cash
"""
PREVIOUS = b"a\n9\n"


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.beancount").write_text(LEDGER)
    (tmp_path / "t.csv").write_text("a,b\n1,2\n")
    (tmp_path / "report.csv").write_bytes(PREVIOUS)
    return tmp_path


def _run(books: Path, module: str, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", module, *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(books, "cli.main", "--no-input", *args)


def _one_line(stderr: str) -> str:
    """The frontend wraps a long message to the terminal width; the engine prints one line."""
    return " ".join(stderr.split())


@pytest.mark.parametrize(
    ("spelling", "message"),
    [
        ("csv:{books}/nope.csv", "No CSV file at '{books}/nope.csv' (from --source csv:{books}/nope.csv)."),
        ("csv:nope.csv", "No CSV file at 'nope.csv' (from --source csv:nope.csv)."),
        ("csv:{books}", "CSV path '{books}' (from --source csv:{books}) is a directory; expected a CSV file."),
        ("", "--source '' names no file; pass a ledger path, beancount:<path> or csv:<path>."),
        ("csv:", "--source 'csv:' names no file; pass a ledger path, beancount:<path> or csv:<path>."),
        ("beancount:", "--source 'beancount:' names no file; pass a ledger path, beancount:<path> or csv:<path>."),
    ],
    ids=["csv-missing", "csv-missing-relative", "csv-directory", "empty", "csv-no-path", "beancount-no-path"],
)
def test_source_that_cannot_be_opened_exits_2_in_one_line(books: Path, spelling: str, message: str) -> None:
    source = spelling.format(books=books)
    result = _bea(books, "query", "--source", source, "SELECT 1", "-f", "csv", "-o", "report.csv")

    assert result.returncode == 2, result.stdout + result.stderr
    # Rich breaks a long path wherever it likes, so compare without whitespace.
    assert "".join(message.format(books=books).split()) in "".join(result.stderr.split())
    assert "Traceback" not in result.stderr
    assert result.stdout == ""
    assert (books / "report.csv").read_bytes() == PREVIOUS


def test_directory_source_reads_like_the_file_option(books: Path) -> None:
    """The note's first command and its control: the same refusal, the same status."""
    source = _bea(books, "query", "--source", str(books), "SELECT 1")
    control = _bea(books, "-f", str(books), "query", "SELECT 1")

    for result, option in ((source, "--source"), (control, "--file")):
        assert result.returncode == 2, result.stdout + result.stderr
        said = "".join(result.stderr.split())
        assert "".join(f"Ledger path '{books}' (from {option}) is a directory; expected a ledger file.".split()) in said
        assert "Traceback" not in result.stderr
        assert result.stdout == ""


@pytest.mark.parametrize("command", ["source-query", "source-shell"])
@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("csv:nope.csv", "No CSV file at 'nope.csv' (from --source)."),
        ("csv:.", "CSV path '.' (from --source) is a directory; expected a CSV file."),
        ("", "--source '' names no file; pass a ledger path, beancount:<path> or csv:<path>."),
    ],
    ids=["csv-missing", "csv-directory", "empty"],
)
def test_engine_refuses_the_path_itself(books: Path, command: str, source: str, message: str) -> None:
    """The backstop: the helper, run without the frontend's check in front of it."""
    query = ["SELECT 1"] if command == "source-query" else []
    result = _run(books, "bea_engine", command, "--output", str(books / "report.csv"), "--", source, *query)

    assert result.returncode == 2, result.stdout + result.stderr
    assert message in result.stderr
    assert len(result.stderr.splitlines()) == 1
    assert result.stdout == ""
    assert (books / "report.csv").read_bytes() == PREVIOUS


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="needs a file the user may not read")
@pytest.mark.parametrize("shell", [False, True], ids=["one-shot", "shell"])
def test_unreadable_source_is_one_line_not_a_traceback(books: Path, shell: bool) -> None:
    """An I/O failure no preflight foresees: the file is there, and the open is refused."""
    secret = books / "secret.csv"
    secret.write_text("a,b\n1,2\n")
    secret.chmod(0)
    try:
        if shell:
            result = _run(books, "bea_engine", "source-shell", "csv:secret.csv")
        else:
            result = _bea(books, "query", "--source", "csv:secret.csv", "SELECT a FROM secret", "-o", "report.csv")
    finally:
        secret.chmod(0o600)

    assert result.returncode == 3, result.stdout + result.stderr
    assert _one_line(result.stderr) == "error: Cannot read the --source: 'secret.csv': Permission denied."
    assert len(result.stderr.splitlines()) == 1
    assert result.stdout == ""
    assert (books / "report.csv").read_bytes() == PREVIOUS


def test_engine_shell_debug_keeps_the_traceback(books: Path) -> None:
    """`--debug` is where a Python traceback is still owed."""
    if not hasattr(os, "geteuid") or os.geteuid() == 0:
        pytest.skip("needs a file the user may not read")
    secret = books / "secret.csv"
    secret.write_text("a,b\n1,2\n")
    secret.chmod(0)
    try:
        result = _run(books, "bea_engine", "source-shell", "--debug", "csv:secret.csv")
    finally:
        secret.chmod(0o600)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "PermissionError" in result.stderr


def test_interactive_missing_csv_never_opens_a_prompt(books: Path) -> None:
    with QueryTerminal(books, ["query", "--source", "csv:nope.csv"]) as shell:
        screen = shell.read()
        assert shell.process.wait(timeout=10) == 2
    assert "No CSV file at 'nope.csv'" in screen.replace("\n", "")
    assert "Traceback" not in screen
    assert "beanquery>" not in screen


@pytest.mark.parametrize("source", ["csv:t.csv", "csv:{books}/t.csv", "csv:t.csv?encoding=utf-8"])
def test_existing_csv_source_still_answers_and_exports(books: Path, source: str) -> None:
    result = _bea(
        books, "query", "--source", source.format(books=books), "SELECT a FROM t", "-f", "csv", "-o", "out.csv"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""
    assert [line.strip() for line in (books / "out.csv").read_text().splitlines()] == ["a", "1"]
