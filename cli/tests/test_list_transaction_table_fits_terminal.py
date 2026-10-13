"""`list transaction` fits the terminal when only the padded table is too wide (w5/164)."""

from __future__ import annotations

import fcntl
import os
import pty
import struct
import subprocess
import sys
import termios
from pathlib import Path

from cli.output import display_width

ROOT = Path(__file__).resolve().parents[1]
# Each row fits 80 columns by itself; the long payee and the long narration sit
# on different rows, so the table padded to both does not.
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking
2026-01-01 open Expenses:Food

2026-01-20 * "Amazon Marketplace Payments WA" "Books"
  Expenses:Food  45.25 USD
  Assets:Checking

2026-01-21 * "Cafe" "Flat white and a croissant x 2"
  Expenses:Food  10.00 USD
  Assets:Checking
"""
ACCOUNT = ("--account", "Expenses:Food")


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k not in {"COLUMNS", "LINES", "CI"}}
    env.update(
        HOME=str(tmp_path / "home"),
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _on_terminal(tmp_path: Path, columns: int, *args: str) -> list[str]:
    """Run `bea list transaction` with stdout on a real pseudo-terminal of this width."""
    ledger = _ledger(tmp_path)
    master, slave = pty.openpty()
    try:
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, columns, 0, 0))
        process = subprocess.Popen(
            [sys.executable, "-m", "cli.main", "--file", str(ledger), "list", "transaction", *args],
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
    return b"".join(chunks).decode().replace("\r\n", "\n").splitlines()


def test_padded_table_never_exceeds_an_80_column_terminal(tmp_path: Path) -> None:
    lines = _on_terminal(tmp_path, 80, *ACCOUNT)

    # The fit is bought with the documented ellipsis, never by dropping a row or a posting amount.
    assert lines == [
        "DATE        FLAG  PAYEE                      NARRATION  MATCHING POSTING AMOUNTS",
        "----------  ----  -------------------------  ---------  ------------------------",
        "2026-01-21  *     Cafe                       Flat w...  Expenses:Food: 10.00 USD",
        "2026-01-20  *     Amazon Marketplace Pay...  Books      Expenses:Food: 45.25 USD",
    ]
    assert [display_width(line) for line in lines] == [80] * 4


def test_unfiltered_padded_table_never_exceeds_the_terminal(tmp_path: Path) -> None:
    """Both postings on the row: each row fits 120 columns, the padded table needs 135."""
    lines = _on_terminal(tmp_path, 120)

    assert max(display_width(line) for line in lines) <= 120, lines
    # Too wide for one line, so the postings go under their row, nothing cut.
    assert lines[2].split() == ["2026-01-21", "*", "Cafe", "Flat", "white", "and", "a", "croissant", "x", "2"]
    assert lines[3:5] == ["  Expenses:Food  : 10.00 USD", "  Assets:Checking: -10.00 USD"]
    assert lines[5].split() == ["2026-01-20", "*", "Amazon", "Marketplace", "Payments", "WA", "Books"]
    assert lines[6:] == ["  Expenses:Food  : 45.25 USD", "  Assets:Checking: -45.25 USD"]


def test_76_column_terminal_keeps_its_shrunk_table(tmp_path: Path) -> None:
    """The control: a row too wide by itself already took the shrink path."""
    assert _on_terminal(tmp_path, 76, *ACCOUNT) == [
        "DATE        FLAG  PAYEE                  NARRATION  MATCHING POSTING AMOUNTS",
        "----------  ----  ---------------------  ---------  ------------------------",
        "2026-01-21  *     Cafe                   Flat w...  Expenses:Food: 10.00 USD",
        "2026-01-20  *     Amazon Marketplace...  Books      Expenses:Food: 45.25 USD",
    ]


def test_table_that_fits_the_terminal_is_printed_whole(tmp_path: Path) -> None:
    lines = _on_terminal(tmp_path, 106, *ACCOUNT)

    assert [display_width(line) for line in lines] == [106] * 4, lines
    assert "Amazon Marketplace Payments WA" in lines[3] and "Flat white and a croissant x 2" in lines[2]


def test_piped_table_keeps_the_full_text(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(_ledger(tmp_path)), "list", "transaction", *ACCOUNT],
        env=_env(tmp_path) | {"COLUMNS": "80"},
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert [len(line) for line in lines] == [106] * 4, lines
    assert "Amazon Marketplace Payments WA" in lines[3] and "Flat white and a croissant x 2" in lines[2]
