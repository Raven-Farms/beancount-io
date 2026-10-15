"""`list`, `balance` and `report` print ledger data as UTF-8 whatever the locale (w5/405).

w5/121 made `format` and `query` stdout UTF-8; the tables and `list
--details` ("in Beancount syntax") still printed in the locale's codec with
`\\u0130`-style escapes, so a saved `--details` named a different payee.
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
    '2026-01-02 * "Zoë" "x"\n  Expenses:İstanbul 5 USD\n  Assets:Cash\n'
    '2026-01-03 * "İPEK" "istanbul"\n  Expenses:İstanbul 2 USD\n  Assets:Cash\n'
)


def _bea(books: Path, *args: str) -> bytes:
    (books / "main.bean").write_text(LEDGER, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONIOENCODING="latin-1",
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["list", "transaction", "--details"], '2026-01-03 * "İPEK" "istanbul"'),
        (["list", "transaction"], "Zoë"),
        (["balance"], "İstanbul"),
        (["report", "income-statement"], "İstanbul"),
    ],
    ids=["details", "table", "balance", "report"],
)
def test_data_is_utf8_under_a_latin1_stdout(tmp_path: Path, args: list[str], expected: str) -> None:
    out = _bea(tmp_path, *args)
    out.decode("utf-8")  # one encoding throughout
    assert expected.encode("utf-8") in out
    assert b"\\u0130" not in out and b"\\xeb" not in out
