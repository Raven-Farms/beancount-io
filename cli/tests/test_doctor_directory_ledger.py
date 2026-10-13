"""`bea doctor <op> DIRECTORY` is a one-line usage error, not a traceback (w5/138).

Upstream's ledger argument accepts any existing path, so a directory reached
`open()` and came back as a raw `IsADirectoryError` traceback with exit 1,
where `bea --file DIRECTORY check` gives one line and exit 2. Every operation
that takes a ledger now refuses a directory the same way before upstream runs.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Each ledger-taking operation, with the extra operands it requires.
OPERATIONS: dict[str, tuple[str, ...]] = {
    "lex": (),
    "dump-lexer": (),
    "parse": (),
    "roundtrip": (),
    "directories": (),
    "print-options": (),
    "context": ("1",),
    "linked": ("1",),
    "region": ("1:1",),
    "missing-open": (),
    "display-context": (),
}


def _bea(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(cwd / "config"),
        XDG_CACHE_HOME=str(cwd / "cache"),
        XDG_DATA_HOME=str(cwd / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _books(tmp_path: Path, name: str = "main.bean") -> Path:
    books = tmp_path / "books"
    books.mkdir()
    (books / name).write_text("2026-01-01 open Assets:Cash\n", encoding="utf-8")
    return books


@pytest.mark.parametrize("op", sorted(OPERATIONS))
def test_directory_ledger_is_a_one_line_usage_error(tmp_path: Path, op: str) -> None:
    _books(tmp_path)

    result = _bea(tmp_path, "doctor", op, "books", *OPERATIONS[op])

    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert "IsADirectoryError" not in result.stderr
    lines = result.stderr.strip().splitlines()
    assert len(lines) == 1, result.stderr
    assert "Ledger path 'books' is a directory; expected a ledger file." in lines[0]
    assert f"bea doctor {op} books/main.bean" in lines[0]
    # Refused before upstream ran: nothing was written beside the ledger.
    assert sorted(path.name for path in (tmp_path / "books").iterdir()) == ["main.bean"]


def test_hint_names_the_root_ledger_the_directory_holds(tmp_path: Path) -> None:
    _books(tmp_path, "main.beancount")

    result = _bea(tmp_path, "doctor", "lex", "books")

    assert result.returncode == 2, result.stderr
    assert "bea doctor lex books/main.beancount" in result.stderr


def test_directory_after_an_option_is_still_the_ledger(tmp_path: Path) -> None:
    _books(tmp_path)

    result = _bea(tmp_path, "doctor", "region", "--conversion", "cost", "books", "1:1")

    assert result.returncode == 2, result.stderr
    assert "Ledger path 'books' is a directory" in result.stderr


@pytest.mark.parametrize("op", ["lex", "dump-lexer", "print-options", "missing-open", "display-context"])
def test_ledger_file_is_still_forwarded(tmp_path: Path, op: str) -> None:
    _books(tmp_path)

    result = _bea(tmp_path, "doctor", op, "books/main.bean")

    assert result.returncode == 0, result.stderr
    assert "is a directory" not in result.stderr


def test_directories_still_takes_directories_after_its_ledger(tmp_path: Path) -> None:
    books = _books(tmp_path)
    (books / "Assets" / "Cash").mkdir(parents=True)

    result = _bea(tmp_path, "doctor", "directories", "books/main.bean", "books")

    assert result.returncode == 0, result.stderr
    assert "is a directory" not in result.stderr


def test_list_options_operand_stays_upstreams_to_reject(tmp_path: Path) -> None:
    _books(tmp_path)

    result = _bea(tmp_path, "doctor", "list-options", "books")

    assert result.returncode == 2
    assert "unexpected extra argument" in result.stderr
    assert "is a directory" not in result.stderr
