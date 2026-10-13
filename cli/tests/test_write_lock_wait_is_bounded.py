"""A writer behind a held lock says it is waiting, and gives up in the end (w5/182).

`lock_file` called a blocking `flock`, so a write queued behind a holder that
never finished — a hung plugin, a stalled filesystem — hung with it: nothing on
stdout or stderr and no time limit, under `--json` and without a terminal too.
"""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from bea_engine import protocol
from bea_engine.ledger import write
from cli.engine import launch

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-02 * "Unaligned"
  Expenses:Food 1.00 USD
  Assets:Cash
"""
ADD = ("add", "transaction", "t", "--date", "2024-02-01", "-p", "Expenses:Food 1.00 USD", "-p", "Assets:Cash")


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    file = tmp_path / "books" / "main.bean"
    file.parent.mkdir()
    file.write_text(LEDGER)
    return file


@contextmanager
def _bea(*args: str, timeout: str | None = None) -> Iterator[subprocess.Popen[bytes]]:
    """A real `bea`, sharing this test's lock directory, stopped if the test gives up on it."""
    env = {k: v for k, v in os.environ.items() if k != "BEA_LOCK_TIMEOUT"}
    env.update(PYTHONPATH=str(ROOT / "src"), NO_COLOR="1")
    if timeout is not None:
        env["BEA_LOCK_TIMEOUT"] = timeout
    child = subprocess.Popen(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    try:
        yield child
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate()


def _finish(child: subprocess.Popen[bytes]) -> tuple[int, str, str]:
    out, err = child.communicate(timeout=60)
    return child.returncode, out.decode(), err.decode()


def _stderr_line_while_running(child: subprocess.Popen[bytes], seconds: float) -> str:
    """The first stderr line, read while the command is still running."""
    assert child.stderr is not None
    deadline = time.monotonic() + seconds
    line = b""
    while not line.endswith(b"\n"):
        ready, _, _ = select.select([child.stderr], [], [], max(0.0, deadline - time.monotonic()))
        assert ready, f"nothing on stderr after {seconds} seconds; got {line!r}"
        chunk = child.stderr.read(1)
        assert chunk, f"the command exited before finishing a line; got {line!r}"
        line += chunk
    assert child.poll() is None, "the line arrived only as the command exited"
    return line.decode()


def test_a_blocked_write_announces_the_wait_then_exits_4(ledger: Path) -> None:
    with write.lock_file(ledger), _bea("-f", str(ledger), *ADD, timeout="6") as child:
        notice = _stderr_line_while_running(child, 30)
        code, out, err = _finish(child)

    assert notice == f"Waiting up to 6 seconds for another bea write on {ledger} ...\n"
    assert code == 4
    assert out == ""
    assert "Timed out after 6 seconds waiting for another bea write" in err
    assert "BEA_LOCK_TIMEOUT" in err
    assert ledger.read_text() == LEDGER


def test_json_mode_gives_up_with_one_error_object(ledger: Path) -> None:
    with write.lock_file(ledger), _bea("--json", "-f", str(ledger), *ADD, timeout="2") as child:
        code, out, err = _finish(child)

    assert code == 4
    assert out == ""
    error = json.loads(err)["error"]  # No notice in front: stderr stays one object.
    assert error["category"] == "conflict"
    assert error["exit_code"] == 4
    assert "Nothing was written" in error["message"]
    assert ledger.read_text() == LEDGER


def test_format_in_place_shares_the_limit_and_zero_does_not_wait(ledger: Path) -> None:
    started = time.monotonic()
    with write.lock_file(ledger), _bea("format", "-i", str(ledger), timeout="0") as child:
        code, out, err = _finish(child)

    assert code == 4
    assert "Timed out after 0 seconds" in err
    assert "Waiting" not in err
    assert ledger.read_text() == LEDGER
    assert time.monotonic() - started < 30


@pytest.mark.skipif(sys.platform == "win32", reason="Windows cannot lock a directory")
def test_the_directory_lock_other_caches_share_is_bounded_too(ledger: Path) -> None:
    with write.lock_directories([ledger]), _bea("-f", str(ledger), *ADD, timeout="2") as child:
        code, out, err = _finish(child)

    assert code == 4
    assert out == ""
    assert f"Waiting up to 2 seconds for another bea write on {ledger.parent} ...\n" in err
    assert "Timed out after 2 seconds" in err
    assert ledger.read_text() == LEDGER


def test_the_waiter_writes_once_the_lock_is_released(ledger: Path) -> None:
    with _bea("-f", str(ledger), *ADD) as child:
        with write.lock_file(ledger):
            notice = _stderr_line_while_running(child, 30)
            assert ledger.read_text() == LEDGER
        code, out, err = _finish(child)

    assert notice == f"Waiting up to 60 seconds for another bea write on {ledger} ...\n"
    assert code == 0, err
    assert out.startswith("Added 1 transaction")
    assert err == ""
    assert ledger.read_text().count("2024-02-01") == 1


def test_an_uncontended_write_and_one_to_another_ledger_say_nothing(ledger: Path) -> None:
    other = ledger.with_name("other.bean")
    other.write_text(LEDGER)

    with _bea("-f", str(ledger), *ADD) as child:
        assert _finish(child) == (0, f"Added 1 transaction to {ledger}.\n", "")
    with write.lock_file(ledger), _bea("-f", str(other), *ADD, timeout="0") as child:
        assert _finish(child) == (0, f"Added 1 transaction to {other}.\n", "")


@pytest.mark.parametrize("value", ["soon", "-1", "inf", "nan"])
def test_an_unusable_timeout_is_a_usage_error(ledger: Path, value: str) -> None:
    with _bea("-f", str(ledger), *ADD, timeout=value) as child:
        code, out, err = _finish(child)

    assert code == 2
    assert out == ""
    assert "BEA_LOCK_TIMEOUT must be a number of seconds" in err
    assert ledger.read_text() == LEDGER


def test_both_sides_of_the_boundary_agree_on_the_notice_prefix() -> None:
    assert launch._NOTICE_PREFIX == protocol.NOTICE_PREFIX
