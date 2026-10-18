"""A plugin's unanchored error refuses or survives a write without crashing (w5/667)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = """import collections
from beancount.core import data
__plugins__ = ["nosrc"]
E = collections.namedtuple("E", "source message entry")
def nosrc(entries, options_map):
    return entries, [E(None, "flagged entry", e) for e in entries
                     if isinstance(e, data.Transaction) and "bad" in e.tags]
"""
BASE = """option "insert_pythonpath" "TRUE"
plugin "nosrc"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening
"""
BAD = '2026-01-05 * "old" #bad\n  Assets:Cash 1 USD\n  Equity:Opening -1 USD\n'


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "nosrc.py").write_text(PLUGIN)
    ledger = tmp_path / "main.bean"
    ledger.write_text(BASE)
    return ledger


def _bea(ledger: Path, *args: str, json_mode: bool) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(ledger.parent / "config"),
        XDG_CACHE_HOME=str(ledger.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    done = subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if json_mode else []), "-f", str(ledger), *args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = json.dumps(json.loads(done.stdout or done.stderr)) if json_mode else done.stdout + done.stderr
    assert "AttributeError" not in output
    assert ".bea-" not in output
    return done.returncode, " ".join(output.split())


@pytest.mark.parametrize("json_mode", [False, True])
@pytest.mark.parametrize("allow_errors", [False, True])
def test_new_error_without_source_refuses_the_write(books: Path, json_mode: bool, allow_errors: bool) -> None:
    before = books.read_bytes()
    code, output = _bea(
        books,
        "add",
        "transaction",
        "new",
        "--date",
        "2026-01-06",
        "-p",
        "Assets:Cash 1 USD",
        "-p",
        "Equity:Opening",
        "--tag",
        "bad",
        *(["--allow-errors"] if allow_errors else []),
        json_mode=json_mode,
    )
    assert code == 1, output
    assert "flagged entry" in output
    assert "<ledger>:0" in output
    assert "nothing was written" in output.lower()
    assert books.read_bytes() == before


@pytest.mark.parametrize("json_mode", [False, True])
def test_existing_error_without_source_is_tolerated_only_when_requested(books: Path, json_mode: bool) -> None:
    books.write_text(BASE + BAD)
    before = books.read_bytes()
    note = ("add", "note", "--date", "2026-01-06", "-a", "Assets:Cash", "-m", "reviewed")
    code, output = _bea(books, "list", "transaction", "--allow-errors", json_mode=json_mode)
    assert code == 0, output
    assert "flagged entry" in output
    code, output = _bea(books, *note, json_mode=json_mode)
    assert code == 1, output
    assert "flagged entry" in output
    assert books.read_bytes() == before
    code, output = _bea(books, *note, "--allow-errors", json_mode=json_mode)
    assert code == 0, output
    assert "flagged entry" in output
    assert '2026-01-06 note Assets:Cash "reviewed"' in books.read_text()


@pytest.mark.parametrize("json_mode", [False, True])
def test_an_additional_unanchored_error_is_not_hidden_by_an_old_one(books: Path, json_mode: bool) -> None:
    books.write_text(BASE + BAD)
    before = books.read_bytes()
    code, output = _bea(
        books,
        "add",
        "transaction",
        "another",
        "--date",
        "2026-01-06",
        "-p",
        "Assets:Cash 2 USD",
        "-p",
        "Equity:Opening",
        "--tag",
        "bad",
        "--allow-errors",
        json_mode=json_mode,
    )
    assert code == 1, output
    assert "flagged entry" in output
    assert books.read_bytes() == before


@pytest.mark.parametrize("json_mode", [False, True])
def test_no_error_control_still_writes(books: Path, json_mode: bool) -> None:
    code, output = _bea(
        books,
        "add",
        "transaction",
        "good",
        "--date",
        "2026-01-06",
        "-p",
        "Assets:Cash 1 USD",
        "-p",
        "Equity:Opening",
        json_mode=json_mode,
    )
    assert code == 0, output
    assert '2026-01-06 * "good"' in books.read_text()


@pytest.mark.parametrize("json_mode", [False, True])
def test_a_different_sourceless_failure_cannot_spend_the_old_error_credit(books: Path, json_mode: bool) -> None:
    (books.parent / "nosrc.py").write_text(
        PLUGIN[: PLUGIN.index("def nosrc")]
        + "def nosrc(entries, options_map):\n"
        + '    message = "new unrelated failure" if any(isinstance(e, data.Note) for e in entries) else "old failure"\n'
        + "    return entries, [E(None, message, None)]\n"
    )
    before = books.read_bytes()
    code, output = _bea(
        books,
        "add",
        "note",
        "--date",
        "2026-01-06",
        "-a",
        "Assets:Cash",
        "-m",
        "reviewed",
        "--allow-errors",
        json_mode=json_mode,
    )
    assert code == 1, output
    assert "new unrelated failure" in output
    assert books.read_bytes() == before
