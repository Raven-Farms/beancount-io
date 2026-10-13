"""Ledger text and query results reach stdout as UTF-8 whatever the locale (w5/121).

stdout escapes what its encoding cannot show so a confirmation line never
undoes exit 0 (w1/104). `bea format FILE > out.bean` wrote through that same
stream, so under an ASCII or cp1252 stdout it exited 0 with `"Müller"` turned
into the literal text `"M\\xfcller"` — a different payee that still loads.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Bank USD
2026-01-01 open Expenses:Food USD
2026-01-02 * "Müller" "Kaffee ☕"
  Expenses:Food  4.50 USD
  Assets:Bank
"""
ENTRY = '2026-01-02 * "Müller" "Kaffee ☕"'.encode()
LOCALES = ["ascii", "cp1252"]


def _bea(tmp_path: Path, encoding: str | None, *args: str) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "PYTHONIOENCODING"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    if encoding is not None:
        env["PYTHONIOENCODING"] = encoding
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


@pytest.mark.parametrize("encoding", LOCALES)
def test_format_to_stdout_matches_the_utf8_run_and_output_file(tmp_path: Path, ledger: Path, encoding: str) -> None:
    expected = _bea(tmp_path, None, "format", str(ledger))
    assert ENTRY in expected  # the control: UTF-8 stdout carries the ledger's own text

    assert _bea(tmp_path, encoding, "format", str(ledger)) == expected

    written = tmp_path / "out.bean"
    _bea(tmp_path, encoding, "format", str(ledger), "-o", str(written))
    assert written.read_bytes() == expected


@pytest.mark.parametrize("encoding", LOCALES)
@pytest.mark.parametrize(
    ("args", "needle"),
    [
        (["PRINT"], ENTRY),
        (["--format", "beancount", "PRINT"], ENTRY),
        (["--format", "csv", "SELECT DISTINCT payee, narration"], "Müller,Kaffee ☕\r\n".encode()),
        (["--format", "text", "SELECT DISTINCT payee, narration"], "Müller  Kaffee ☕".encode()),
    ],
    ids=["print", "beancount", "csv", "text"],
)
def test_query_results_match_the_utf8_run(
    tmp_path: Path, ledger: Path, encoding: str, args: list[str], needle: bytes
) -> None:
    expected = _bea(tmp_path, None, "--file", str(ledger), "query", *args)
    assert needle in expected

    assert _bea(tmp_path, encoding, "--file", str(ledger), "query", *args) == expected


@pytest.mark.parametrize("encoding", LOCALES)
def test_a_confirmation_line_is_still_escaped_not_fatal(tmp_path: Path, encoding: str) -> None:
    books = tmp_path / "☕"
    books.mkdir()
    target = books / "main.bean"
    target.write_text(LEDGER, encoding="utf-8")
    args = ["--file", str(target), "add", "transaction", "--date", "2026-02-01", "--narration", "x"]
    args += ["--posting", "Expenses:Food 1 USD", "--posting", "Assets:Bank"]

    done = _bea(tmp_path, encoding, *args)

    assert b"Added 1 transaction" in done
    assert b"\\u2615" in done  # escaped, not a crash
    assert target.read_bytes().count(b'2026-02-01 * "x"') == 1
