"""A ledger nobody may delete refuses a write cleanly (w5/257).

The staged copy is given the ledger's ACL before the rename (w1/099). A
deny-delete entry refuses that rename, and then refused removing the copy as
well: the cleanup's raw `Errno 13` replaced the "refused to replace" refusal
(exit 1, category `validation`) and every attempt left a `.bea-<hex>.tmp`
copy of the ledger behind that the user could not delete either.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS ACLs")

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"

2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD

2026-01-02 * "Misaligned"
  Expenses:Food 1 USD
  Assets:Checking
"""

WRITES = {
    "add transaction": [
        *("add", "transaction", "--date", "2026-01-05", "--narration", "Lunch"),
        *("--posting", "Expenses:Food 10 USD", "--posting", "Assets:Checking"),
    ],
    "add note": ["add", "note", "--date", "2026-01-05", "-a", "Assets:Checking", "-m", "hi"],
    "format -i": ["format", "-i", "main.bean"],
}


@pytest.fixture
def books(tmp_path: Path) -> Iterator[Path]:
    directory = tmp_path / "books"
    directory.mkdir()
    (directory / "main.bean").write_text(LEDGER)
    yield directory
    # Whatever a failing run left carries the ACL too, and pytest could not clear it.
    for path in directory.iterdir():
        subprocess.run(["chmod", "-N", str(path)], check=False)


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books.parent / "config"),
        XDG_CACHE_HOME=str(books.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _staged(books: Path) -> list[str]:
    return sorted(path.name for path in books.iterdir() if path.name != "main.bean")


@pytest.mark.parametrize("write", WRITES)
def test_a_deny_delete_ledger_refuses_the_write_and_leaves_no_copy(books: Path, write: str) -> None:
    file = books / "main.bean"
    subprocess.run(["chmod", "+a", "everyone deny delete", str(file)], check=True)

    result = _bea(books, "--file", "main.bean", *WRITES[write])

    assert result.returncode == 3, result.stderr
    message = " ".join(result.stderr.split())
    assert "The filesystem refused to replace" in message
    assert "main.bean" in message
    assert "nothing was written" in message
    assert "PermissionError" not in message
    assert ".tmp" not in message
    assert _staged(books) == []
    assert file.read_text() == LEDGER
    listing = subprocess.run(["ls", "-le", str(file)], check=True, capture_output=True, text=True).stdout
    assert "deny delete" in listing


def test_the_refusal_is_an_auth_error_in_json(books: Path) -> None:
    subprocess.run(["chmod", "+a", "everyone deny delete", str(books / "main.bean")], check=True)

    result = _bea(books, "--json", "--file", "main.bean", *WRITES["add note"])

    assert result.returncode == 3, result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "auth"
    assert error["exit_code"] == 3
    assert "refused to replace" in error["message"]
    assert _staged(books) == []


@pytest.mark.parametrize("write", WRITES)
def test_a_ledger_without_the_acl_is_written_as_before(books: Path, write: str) -> None:
    file = books / "main.bean"

    result = _bea(books, "--file", "main.bean", *WRITES[write])

    assert result.returncode == 0, result.stderr
    assert _staged(books) == []
    assert file.read_text() != LEDGER
