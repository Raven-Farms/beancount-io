"""A one-shot dot command is one line, and its failure is not success (w5/236).

Text opening with a dot command skipped the one-statement rule and went whole
to the shell, where the following lines became the command's argument: the
query never ran, upstream printed `error:` and returned, and the one-shot
exited 0 — with an empty JSON success envelope, or over an emptied `-o` export.
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
option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Cafe" "Coffee"
  Expenses:Food  4.00 USD
  Assets:Cash
2026-01-01 query "b-good" "SELECT count(*) AS n"
"""
KEPT = "LAST GOOD EXPORT\n"
FILE = ["--file", "main.bean", "query"]
SOURCE = ["query", "--source", "main.bean"]


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    (tmp_path / "keep.csv").write_text(KEPT, encoding="utf-8")
    return tmp_path


def _bea(books: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        HOME=str(books / "home"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        cwd=books,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("surface", [FILE, SOURCE], ids=["file", "source"])
def test_lines_after_a_dot_command_are_refused_and_the_export_survives(books: Path, surface: list[str]) -> None:
    result = _bea(books, *surface, "-o", "keep.csv", stdin=".format csv\nSELECT count(*) AS n;\n")

    assert result.returncode == 2, result.stderr
    assert "One command per invocation" in result.stderr
    assert "`.format`" in result.stderr
    assert result.stdout == ""
    assert (books / "keep.csv").read_text(encoding="utf-8") == KEPT


@pytest.mark.parametrize("text", [".tables\n.run b-good\n", "help\nSELECT count(*) AS n"])
def test_a_second_line_is_refused_instead_of_dropped(books: Path, text: str) -> None:
    result = _bea(books, *FILE, stdin=text)

    assert result.returncode == 2, result.stderr
    assert "One command per invocation" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("surface", [FILE, SOURCE], ids=["file", "source"])
@pytest.mark.parametrize(
    ("command", "complaint"),
    [
        (".bogus", 'unknown command "bogus"'),
        (".set a b c", "invalid number of arguments"),
        (".set nope", 'variable "nope" does not exist'),
        (".format xml", '"xml" is not a valid format'),
    ],
)
def test_a_rejected_dot_command_exits_2_and_writes_no_export(
    books: Path, surface: list[str], command: str, complaint: str
) -> None:
    result = _bea(books, *surface, "-o", "keep.csv", command)

    assert result.returncode == 2, result.stderr
    assert f"Cannot run this shell command: {complaint}." in result.stderr
    assert "Traceback" not in result.stderr
    assert (books / "keep.csv").read_text(encoding="utf-8") == KEPT


def test_a_rejected_dot_command_is_a_json_usage_error(books: Path) -> None:
    result = _bea(books, "--json", *FILE, "-o", "keep.csv", ".bogus")

    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert error["exit_code"] == 2
    assert 'unknown command "bogus"' in error["message"]
    assert (books / "keep.csv").read_text(encoding="utf-8") == KEPT


@pytest.mark.parametrize("surface", [FILE, SOURCE], ids=["file", "source"])
def test_a_single_dot_command_still_works(books: Path, surface: list[str]) -> None:
    # Trailing blank lines are not further commands.
    tables = _bea(books, *surface, stdin=".tables\n\n")
    assert tables.returncode == 0, tables.stderr
    assert "postings" in tables.stdout.split()

    stored = _bea(books, *surface, ".run b-good")
    assert stored.returncode == 0, stored.stderr
    assert stored.stdout.split() == ["n", "-", "2"]

    exported = _bea(books, *surface, "-o", "keep.csv", ".tables")
    assert exported.returncode == 0, exported.stderr
    assert "postings" in (books / "keep.csv").read_text(encoding="utf-8").split()


def test_a_single_dot_command_keeps_its_json_text_envelope(books: Path) -> None:
    result = _bea(books, "--json", *FILE, ".tables")

    assert result.returncode == 0, result.stderr
    assert "postings" in json.loads(result.stdout)["data"]["text"].split()


@pytest.mark.parametrize("command", [".explain", ".parse"])
def test_commands_that_take_bql_may_span_lines(books: Path, command: str) -> None:
    result = _bea(books, *FILE, stdin=f"{command} SELECT\n  count(*) AS n\n")

    assert result.returncode == 0, result.stderr
    assert "fname: 'count'" in result.stdout


@pytest.mark.parametrize("surface", [FILE, SOURCE], ids=["file", "source"])
def test_a_mistake_in_the_init_file_stays_a_note(books: Path, surface: list[str]) -> None:
    # Not the caller's command: upstream's `error:` line, and the query answers.
    init = books / "home" / ".config" / "beanquery" / "init"
    init.parent.mkdir(parents=True)
    init.write_text(".bogus\n", encoding="utf-8")

    result = _bea(books, *surface, "SELECT count(*) AS n")

    assert result.returncode == 0, result.stderr
    assert 'unknown command "bogus"' in result.stderr
    assert result.stdout.split() == ["n", "-", "2"]
