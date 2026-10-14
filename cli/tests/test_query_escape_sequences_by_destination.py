"""One-shot `bea query` keeps escape sequences in exported data and off the terminal (w5/245)."""

from __future__ import annotations

import os
import pty
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ESC = "\x1b"
LEDGER = f"""option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-04 * "ACME{ESC}[1mCORP{ESC}[0m" "ref{ESC}[2K7"
  Expenses:Food  10.00 USD
  Assets:Checking
"""
SELECT = "SELECT payee, narration WHERE account ~ 'Food'"
# format, query, and the payee as a file or pipe must hold it.
EXPORTS = [
    ("csv", SELECT, f"ACME{ESC}[1mCORP{ESC}[0m,ref{ESC}[2K7"),
    ("beancount", "PRINT", f'"ACME{ESC}[1mCORP{ESC}[0m" "ref{ESC}[2K7"'),
    ("text", "PRINT", f'"ACME{ESC}[1mCORP{ESC}[0m" "ref{ESC}[2K7"'),
]
IDS = ["csv", "beancount-print", "text-print"]
VISIBLE = "ACME\\x1b[1mCORP\\x1b[0m"


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k not in {"COLUMNS", "CI"}}
    env.update(
        HOME=str(tmp_path / "home"),
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="xterm-256color",
    )
    return env


def _argv(tmp_path: Path, *args: str) -> list[str]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return [sys.executable, "-m", "cli.main", "--file", str(ledger), "query", *args]


def _piped(tmp_path: Path, *args: str) -> bytes:
    result = subprocess.run(
        _argv(tmp_path, *args),
        env=_env(tmp_path),
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert result.stderr == b""
    return result.stdout


def _on_terminal(tmp_path: Path, *args: str) -> bytes:
    """Everything the query sends to a real pseudo-terminal on stdout."""
    master, slave = pty.openpty()
    try:
        process = subprocess.Popen(
            _argv(tmp_path, *args),
            env=_env(tmp_path),
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            stdout=slave,
            stderr=subprocess.PIPE,
        )
        os.close(slave)
        slave = -1
        chunks = []
        while True:
            try:
                chunk = os.read(master, 4096)
            except OSError:  # Linux reports the closed slave as EIO, macOS as EOF.
                break
            if not chunk:
                break
            chunks.append(chunk)
        _, stderr = process.communicate(timeout=60)
    finally:
        if slave >= 0:
            os.close(slave)
        os.close(master)
    assert process.returncode == 0, stderr.decode()
    return b"".join(chunks)


@pytest.mark.parametrize(("fmt", "query", "payee"), EXPORTS, ids=IDS)
def test_a_pipe_and_an_output_file_hold_the_same_verbatim_bytes(
    tmp_path: Path, fmt: str, query: str, payee: str
) -> None:
    piped = _piped(tmp_path, "-f", fmt, query)
    exported = tmp_path / "out.txt"
    assert _piped(tmp_path, "-f", fmt, "-o", str(exported), query) == b""

    assert payee.encode() in piped
    assert exported.read_bytes() == piped


@pytest.mark.parametrize(("fmt", "query", "payee"), EXPORTS, ids=IDS)
def test_a_terminal_is_shown_the_escape_instead_of_receiving_it(
    tmp_path: Path, fmt: str, query: str, payee: str
) -> None:
    screen = _on_terminal(tmp_path, "-f", fmt, query)

    assert ESC.encode() not in screen
    assert VISIBLE.encode() in screen
    assert b"ref\\x1b[2K7" in screen
    # Nothing but the control characters changed: the terminal shows the piped
    # result line for line (the PTY's own CRLF translation aside).
    visible = _piped(tmp_path, "-f", fmt, query).decode().replace(ESC, "\\x1b")
    assert screen.decode().replace("\r", "").splitlines() == visible.splitlines()


def test_the_text_table_is_the_same_everywhere(tmp_path: Path) -> None:
    piped = _piped(tmp_path, "-f", "text", SELECT)

    assert ESC.encode() not in piped
    assert VISIBLE.encode() in piped
    assert _on_terminal(tmp_path, "-f", "text", SELECT).replace(b"\r\n", b"\n") == piped
