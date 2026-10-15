"""Forwarded upstream programs write UTF-8 whatever the locale (w5/404).

They ran with the locale's codec in strict mode, so under a Latin-1 or
cp1252 locale `treeify` failed with a `UnicodeEncodeError` class name and
`doctor context` with an upstream traceback on `İstanbul`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:İstanbul USD\n'
    '2026-01-03 * "İPEK" "istanbul"\n  Expenses:İstanbul 5 USD\n  Assets:Cash\n'
)


def _bea(books: Path, *args: str, latin1: bool = True) -> subprocess.CompletedProcess[bytes]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    if latin1:
        env["PYTHONIOENCODING"] = "latin-1"
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=books,
        capture_output=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    balances = _bea(
        tmp_path, "-f", "main.bean", "query", "SELECT account, sum(position) GROUP BY account", latin1=False
    )
    assert balances.returncode == 0, balances.stderr
    (tmp_path / "bal.txt").write_bytes(balances.stdout)
    return tmp_path


@pytest.mark.parametrize(
    ("args", "expected"),
    [(["treeify", "bal.txt"], "İstanbul"), (["doctor", "context", "main.bean", "4"], '"İPEK" "istanbul"')],
    ids=["treeify", "doctor-context"],
)
def test_upstream_output_is_utf8_under_a_latin1_locale(books: Path, args: list[str], expected: str) -> None:
    result = _bea(books, *args)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert expected.encode("utf-8") in result.stdout
    assert b"UnicodeEncodeError" not in result.stderr
    assert b"Traceback" not in result.stderr
