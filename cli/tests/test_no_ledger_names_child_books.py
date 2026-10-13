"""The no-ledger error points at books one directory down (w5/219).

Running the quick start without `cd books` produced an error whose only
copy-pasteable command was `bea init books --currency USD`, which can only
refuse because `books/main.bean` already exists.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INIT_HINT = "To start new books, run bea init books --currency USD."


def _bea(tmp_path: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


ADD = ("add", "transaction", "Coffee", "--date", "2026-08-02", "--posting", "Expenses:Dining 12.50")


def test_error_after_init_names_the_new_books_and_the_pointer_works(tmp_path: Path) -> None:
    cwd = tmp_path / "g1"
    cwd.mkdir()
    made = _bea(tmp_path, cwd, "--no-input", "init", "books", "--currency", "USD", "--date", "2026-08-01")
    assert made.returncode == 0, made.stderr

    result = _bea(tmp_path, cwd, *ADD, "--posting", "Assets:Checking")

    assert result.returncode == 2
    assert "No ledger file at 'main.bean' (from the working directory)." in result.stderr
    assert "Found books/main.bean here: run cd books, or pass --file books/main.bean." in result.stderr
    assert "bea init" not in result.stderr
    # The pointer is a real way forward, unlike the init it replaces.
    followed = _bea(tmp_path, cwd, "--file", "books/main.bean", "check")
    assert followed.returncode == 0, followed.stderr


def test_json_error_names_the_child_ledger(tmp_path: Path) -> None:
    cwd = tmp_path / "g1"
    (cwd / "books").mkdir(parents=True)
    (cwd / "books" / "main.bean").write_text("2024-01-01 open Assets:Cash USD\n")

    result = _bea(tmp_path, cwd, "--json", "check")

    assert result.returncode == 2
    message = json.loads(result.stdout or result.stderr)["error"]["message"]
    assert "--file books/main.bean" in message
    assert "bea init" not in message


@pytest.mark.parametrize(
    ("child", "name", "quoted_dir", "quoted_file"),
    [
        ("ledger", "main.beancount", "ledger", "ledger/main.beancount"),
        ("my books", "main.bean", "'my books'", "'my books/main.bean'"),
    ],
)
def test_pointer_follows_the_fallback_name_and_is_shell_quoted(
    tmp_path: Path, child: str, name: str, quoted_dir: str, quoted_file: str
) -> None:
    cwd = tmp_path / "g1"
    (cwd / child).mkdir(parents=True)
    (cwd / child / name).write_text("2024-01-01 open Assets:Cash USD\n")

    result = _bea(tmp_path, cwd, "check")

    assert result.returncode == 2
    assert f"run cd {quoted_dir}, or pass --file {quoted_file}." in result.stderr
    assert INIT_HINT not in result.stderr


def test_first_child_by_name_wins_and_hidden_directories_are_ignored(tmp_path: Path) -> None:
    cwd = tmp_path / "g1"
    for child in (".cache", "zeta", "alpha"):
        (cwd / child).mkdir(parents=True)
        (cwd / child / "main.bean").write_text("2024-01-01 open Assets:Cash USD\n")

    result = _bea(tmp_path, cwd, "check")

    assert result.returncode == 2
    assert "--file alpha/main.bean" in result.stderr
    assert ".cache" not in result.stderr


def test_empty_directory_keeps_the_init_suggestion_and_it_succeeds(tmp_path: Path) -> None:
    cwd = tmp_path / "empty"
    cwd.mkdir()
    # A child without a root ledger, and a grandchild ledger, are not books here.
    (cwd / "notes" / "deep").mkdir(parents=True)
    (cwd / "notes" / "deep" / "main.bean").write_text("2024-01-01 open Assets:Cash USD\n")

    result = _bea(tmp_path, cwd, *ADD, "--posting", "Assets:Checking")

    assert result.returncode == 2
    assert result.stderr.strip() == (
        "Error: No ledger file at 'main.bean' (from the working directory). Name one with --file PATH, "
        "set BEA_FILE, or run from a directory containing main.bean or main.beancount. " + INIT_HINT
    )
    made = _bea(tmp_path, cwd, "--no-input", "init", "books", "--currency", "USD")
    assert made.returncode == 0, made.stderr


def test_missing_explicit_file_does_not_point_at_child_books(tmp_path: Path) -> None:
    cwd = tmp_path / "g1"
    (cwd / "books").mkdir(parents=True)
    (cwd / "books" / "main.bean").write_text("2024-01-01 open Assets:Cash USD\n")

    result = _bea(tmp_path, cwd, "--file", "absent.bean", "check")

    assert result.returncode == 2
    assert "No ledger file at 'absent.bean' (from --file)." in result.stderr
    assert INIT_HINT in result.stderr
