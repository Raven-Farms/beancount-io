"""`doctor missing-open`, `linked` and `region` refuse a ledger a syntax error left partial (w5/596).

The loader skips an unparseable directive and carries on, so `missing-open`
listed the opens of what it could parse with exit 0, and nothing mentioned
the error. `linked` showed half a link group the same way. `print-options`
and `roundtrip` already refused.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = 'option "operating_currency" "USD"\ninclude "sub/jan.bean"\n2026-01-01 open Assets:Bank USD\n'
JAN = """\
2026-01-10 * "Ok" ^trip
  Expenses:Rent 9.00 USD
  Assets:Bank
2026-01-11 * "Cafe" "Broken
  Expenses:Food 4.50 USD
  Assets:Bank
2026-01-12 * "X" "Y" ^trip
  Expenses:Coffee 1.00 USD
  Assets:Bank
"""


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "sub").mkdir()
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "sub" / "jan.bean").write_text(JAN)
    return tmp_path


def _doctor(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "doctor", *args],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


OPERATIONS = {
    "missing-open": lambda books: ["missing-open", str(books / "main.bean")],
    "linked": lambda books: ["linked", str(books / "main.bean"), f"{books / 'sub' / 'jan.bean'}:1"],
    "region": lambda books: ["region", str(books / "main.bean"), f"{books / 'sub' / 'jan.bean'}:1:3"],
}


@pytest.mark.parametrize("op", sorted(OPERATIONS))
def test_a_syntax_error_in_an_include_is_named_before_any_output(books: Path, op: str) -> None:
    result = _doctor(books, *OPERATIONS[op](books))

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout == ""
    message = " ".join(result.stderr.split())
    assert f"doctor {op} cannot load {books / 'main.bean'}: {books / 'sub' / 'jan.bean'}:7:" in message


def test_with_the_quote_closed_missing_open_lists_every_account(books: Path) -> None:
    (books / "sub" / "jan.bean").write_text(JAN.replace('"Broken\n', '"Broken"\n'))

    result = _doctor(books, *OPERATIONS["missing-open"](books))

    assert result.returncode == 0, result.stderr
    assert [line.split()[-1] for line in result.stdout.splitlines() if line.strip()] == [
        "Expenses:Rent",
        "Expenses:Food",
        "Expenses:Coffee",
    ]
