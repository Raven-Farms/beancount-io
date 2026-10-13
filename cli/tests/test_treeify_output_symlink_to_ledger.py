"""`treeify -o LINK` judges a symlink by the ledger it resolves to (w5/159)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Assets:Bank:Checking USD\n"
BALANCES = (
    "account               sum\n"
    "Assets:Bank:Checking  500.00 USD\n"
    "Assets:Bank:Savings    50.00 USD\n"
    "Assets:Cash             5.00 USD\n"
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path / "books",
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    directory = tmp_path / "books"
    directory.mkdir()
    (directory / "books.bean").write_text(LEDGER)
    (directory / "bal.txt").write_text(BALANCES)
    return directory


def _link(books: Path, shape: str) -> None:
    if shape == "direct":
        (books / "latest").symlink_to("books.bean")
    else:
        (books / "current").symlink_to("books.bean")
        (books / "latest").symlink_to("current")


@pytest.mark.parametrize("shape", ["direct", "chain"])
@pytest.mark.parametrize("flag", ["-o", "--output"])
def test_a_suffixless_link_to_a_ledger_is_refused(tmp_path: Path, books: Path, shape: str, flag: str) -> None:
    _link(books, shape)

    result = _bea(tmp_path, "treeify", "bal.txt", flag, "latest")

    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    assert f"Already exists: {(books / 'books.bean').resolve()}." in " ".join(result.stderr.split())
    assert "--force" in result.stderr
    assert (books / "books.bean").read_text() == LEDGER
    assert (books / "latest").is_symlink()


def test_the_ledger_named_directly_is_still_refused(tmp_path: Path, books: Path) -> None:
    """The control: the plain spelling keeps its refusal and its wording."""
    result = _bea(tmp_path, "treeify", "bal.txt", "-o", "books.bean")

    assert result.returncode == 2, result.stderr
    assert "Already exists: books.bean." in result.stderr
    assert (books / "books.bean").read_text() == LEDGER


def test_force_still_overwrites_through_the_link(tmp_path: Path, books: Path) -> None:
    _link(books, "direct")

    result = _bea(tmp_path, "treeify", "bal.txt", "--force", "-o", "latest")

    assert result.returncode == 0, result.stderr
    assert "`-- Assets" in (books / "books.bean").read_text()
    assert (books / "latest").is_symlink()


def test_a_link_to_a_file_that_is_not_a_ledger_is_still_written(tmp_path: Path, books: Path) -> None:
    """Only a ledger behind the link is protected; an ordinary report target is not."""
    (books / "tree.txt").write_text("old report\n")
    (books / "latest").symlink_to("tree.txt")

    result = _bea(tmp_path, "treeify", "bal.txt", "-o", "latest")

    assert result.returncode == 0, result.stderr
    assert "`-- Assets" in (books / "tree.txt").read_text()
    assert (books / "books.bean").read_text() == LEDGER
