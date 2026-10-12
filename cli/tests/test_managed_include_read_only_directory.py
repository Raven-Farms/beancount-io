"""Reading a ledger with a managed price include from a read-only directory says so as a read (w5/095).

Resolving the include parses temporary copies beside each ledger file. In a
read-only directory `list`, `check` and `balance` failed with the write path's
message about validating a write nobody had asked for.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.test_price import _run_bea, _write_managed_ledger
from tests.test_price import feed_server as feed_server

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permissions that bind the current user",
)

READS = [["list", "open"], ["check"], ["balance"], ["price", "status"]]


@pytest.fixture
def frozen(tmp_path: Path, feed_server: str) -> Iterator[tuple[Path, Path]]:
    books = tmp_path / "books"
    books.mkdir()
    ledger = _write_managed_ledger(books, feed_server)
    ledger.chmod(0o444)
    books.chmod(0o555)
    yield tmp_path, ledger
    books.chmod(0o755)


@pytest.mark.parametrize("command", READS, ids=[" ".join(command) for command in READS])
def test_a_read_is_refused_as_a_read(frozen: tuple[Path, Path], feed_server: str, command: list[str]) -> None:
    tmp_path, ledger = frozen

    result = _run_bea(tmp_path, feed_server, "--file", str(ledger), *command)

    assert result.returncode == 3, result.stdout + result.stderr
    message = " ".join(result.stderr.split())
    assert f"Cannot read {ledger}" in message
    assert f"{feed_server}/prices/BTC-USD" in message
    assert "validates a write" not in message and "Cannot stage" not in message
    assert "bea price export" in message
    assert sorted(path.name for path in ledger.parent.iterdir()) == ["main.bean"]


def test_a_write_keeps_the_write_refusal(frozen: tuple[Path, Path], feed_server: str) -> None:
    tmp_path, ledger = frozen
    ledger.parent.chmod(0o755)
    ledger.chmod(0o644)
    ledger.parent.chmod(0o555)

    result = _run_bea(
        tmp_path,
        feed_server,
        "--file",
        str(ledger),
        "add",
        "note",
        "-a",
        "Assets:Cash",
        "-m",
        "x",
        "--date",
        "2026-09-12",
    )

    assert result.returncode == 3, result.stdout + result.stderr
    assert "Cannot read" not in result.stderr


def test_the_same_ledger_reads_once_the_directory_is_writable(tmp_path: Path, feed_server: str) -> None:
    ledger = _write_managed_ledger(tmp_path, feed_server)

    result = _run_bea(tmp_path, feed_server, "--file", str(ledger), "list", "price")

    assert result.returncode == 0, result.stderr
    assert "112000.00 USD" in result.stdout
