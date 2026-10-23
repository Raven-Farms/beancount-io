"""A CSV mixing UTF-8 and cp1252 lines is named as mixed, not sent to cp1252 (w5/406).

cp1252 reads every byte, so the decode check suggested it for a file whose
other lines were UTF-8, and following the advice wrote `CafÃ©`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = b"Date,Payee,Narration,Amount\n"


def _import(books: Path, csv: bytes) -> subprocess.CompletedProcess[str]:
    (books / "main.bean").write_text(
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'
        "2026-01-01 open Expenses:Uncategorized USD\n"
    )
    (books / "s.csv").write_bytes(csv)
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
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "import", "s.csv"]
        + ["--csv", "date=Date,payee=Payee,narration=Narration,amount=Amount", "--account", "Assets:Cash"],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_a_mixed_file_names_both_lines_and_no_cp1252(tmp_path: Path) -> None:
    result = _import(tmp_path, HEADER + b"2026-01-07,Caf\xc3\xa9,a,-3.00\n2026-01-08,Caf\xe9,b,-4.00\n")
    assert result.returncode == 2
    assert "s.csv mixes encodings: line 2 is UTF-8 with accented characters, while line 3 is not UTF-8" in (
        result.stderr
    )
    assert "encoding=cp1252" not in result.stderr


def test_a_pure_cp1252_file_still_gets_the_hint(tmp_path: Path) -> None:
    result = _import(tmp_path, HEADER + b"2026-01-08,Caf\xe9,b,-4.00\n")
    assert result.returncode == 2
    assert "Re-save the export as UTF-8" in result.stderr
    assert "pass --csv encoding=cp1252 only if" in result.stderr
