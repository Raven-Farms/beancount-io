"""`import` on a ledger with a Latin-1 comment byte names the decode problem (w5/441).

Such a ledger loads (w5/278), but the import preview built its diff with an
unguarded UTF-8 decode, so preview and `--apply` died with a bare
`UnicodeDecodeError` where `add` says how to fix the file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    b'option "operating_currency" "USD"\n; caf\xe9 comment\n'
    b"2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Uncategorized USD\n"
)
IMPORT = ["import", "s.csv", "--account", "Assets:Cash", "--csv", "date=Date,narration=Narration,amount=Amount"]


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "--json", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("apply", [[], ["--apply"]], ids=["preview", "apply"])
def test_import_names_the_byte_and_the_remedy(tmp_path: Path, apply: list[str]) -> None:
    (tmp_path / "main.bean").write_bytes(LEDGER)
    (tmp_path / "s.csv").write_text("Date,Narration,Amount\n2026-01-05,food,-5.00\n")
    assert _bea(tmp_path, "check").returncode == 0

    result = _bea(tmp_path, *IMPORT, *apply)

    assert result.returncode == 1, result.stderr
    message = json.loads(result.stderr)["error"]["message"]
    assert message == (
        f"Cannot decode '{tmp_path / 'main.bean'}' as UTF-8: invalid continuation byte at byte 39. "
        "Re-save the file as UTF-8 and retry."
    )
    assert (tmp_path / "main.bean").read_bytes() == LEDGER
