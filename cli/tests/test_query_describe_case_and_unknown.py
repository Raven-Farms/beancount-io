"""`.describe` folds case like `FROM`, and refuses names it cannot find (w5/749).

`.describe Accounts` exited 0 with no output — upstream looks tables up
case-sensitively — and so did `.describe nope`, which an agent can read as
"no columns". The first now lists the columns; the second is a usage error.
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
"""


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    return tmp_path


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        cwd=books,
        stdin=subprocess.DEVNULL,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("name", ["accounts", "Accounts", "ACCOUNTS"])
def test_describe_folds_table_case(books: Path, name: str) -> None:
    result = _bea(books, "--file", "main.bean", "query", f".describe {name}")

    assert result.returncode == 0, result.stderr
    assert "account (str)" in result.stdout, result.stdout
    assert "open (open)" in result.stdout, result.stdout


def test_describe_folds_type_case(books: Path) -> None:
    result = _bea(books, "--file", "main.bean", "query", ".describe DATE")

    assert result.returncode == 0, result.stderr
    assert "structured type" in result.stdout, result.stdout
    assert "year (int)" in result.stdout, result.stdout


@pytest.mark.parametrize("extra", [[], ["--json"]])
def test_describe_refuses_an_unknown_name(books: Path, extra: list[str]) -> None:
    text = _bea(books, *extra, "--file", "main.bean", "query", ".describe nope")

    assert text.returncode == 2, text.stdout + text.stderr
    assert "Traceback" not in text.stderr
    if extra:
        error = json.loads(text.stderr)["error"]
        assert (error["category"], error["exit_code"]) == ("usage", 2)
        assert '"nope"' in error["message"], error
    else:
        assert '"nope"' in text.stderr, text.stderr


def test_describe_refuses_an_unknown_name_on_source(books: Path) -> None:
    result = _bea(books, "query", "--source", "main.bean", ".describe nope")

    assert result.returncode == 2, result.stdout + result.stderr
    assert '"nope"' in result.stderr, result.stderr


def test_describe_names_the_unknown_one_among_known(books: Path) -> None:
    result = _bea(books, "--file", "main.bean", "query", ".describe accounts nope")

    assert result.returncode == 2, result.stdout + result.stderr
    assert '"nope"' in result.stderr, result.stderr


def test_describe_json_lists_folded_columns(books: Path) -> None:
    result = _bea(books, "--json", "--file", "main.bean", "query", ".describe Postings")

    assert result.returncode == 0, result.stderr
    assert "table " in json.loads(result.stdout)["data"]["text"], result.stdout
