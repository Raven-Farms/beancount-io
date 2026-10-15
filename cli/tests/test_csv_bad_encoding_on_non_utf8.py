"""A bad `--csv encoding=` is named on a non-UTF-8 export too (w5/332).

The early parse swallowed the bad key, the file was decoded as UTF-8, and the
generic decode refusal told the user to force an encoding — what they had
just tried — while claiming latin-1, which reads any byte, had failed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Uncategorized\n'
)
MAPPING = "date=Date,payee=Payee,amount=Amount"


def _import(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "--no-input",
            "-f",
            "main.bean",
            "import",
            *args,
            "--account",
            "Assets:Checking",
        ],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "sj.csv").write_bytes("Date,Payee,Amount\n2026-02-03,東京ラーメン,-9.00\n".encode("shift_jis"))
    return tmp_path


@pytest.mark.parametrize("spec", [f"{MAPPING},encoding=sjis", f"{MAPPING},encoding=bogus", "encoding=iso8859-1"])
def test_the_bad_key_is_named_before_the_file_is_read(books: Path, spec: str) -> None:
    value = spec.rsplit("=", 1)[1]
    result = _import(books, "sj.csv", "--csv", spec)
    assert result.returncode == 2
    assert f"Bad --csv encoding '{value}': write utf-8, cp1252, or latin-1." in result.stderr
    assert "Cannot decode" not in result.stderr


def test_without_the_key_latin1_is_not_claimed_to_fail(books: Path) -> None:
    result = _import(books, "sj.csv", "--csv", MAPPING)
    message = " ".join(result.stderr.split())
    assert result.returncode == 2
    assert "Cannot decode sj.csv as UTF-8 or cp1252" in message
    assert "tried utf-8, cp1252, latin-1" not in message
