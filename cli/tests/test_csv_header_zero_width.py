"""A doubled BOM or a zero-width character in a CSV header is dropped, as in amount cells (w5/531).

Header cells got only `strip()` and NFC, so a doubled BOM before `Date` or a
U+200B after `Description` left the column unmatchable while the refusal
printed it plain, and its own `--csv date=Date,…` advice then failed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Uncategorized USD
"""
ROW = b"2026-03-01,Coffee,-4.50\n"


@pytest.mark.parametrize(
    "header",
    [
        b"\xef\xbb\xbf\xef\xbb\xbfDate,Description,Amount\n",
        b"Date,Description\xe2\x80\x8b,Amount\n",
        b"Date\xe2\x81\xa0,Description,Amount\n",
    ],
    ids=["double-bom", "zero-width-space", "word-joiner"],
)
@pytest.mark.parametrize(
    "mapping", [(), ("--csv", "date=Date,amount=Amount,narration=Description")], ids=["inferred", "explicit"]
)
def test_the_header_matches(tmp_path: Path, header: bytes, mapping: tuple[str, ...]) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_bytes(header + ROW)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "import", "bank.csv", *mapping]
        + ["--account", "Assets:Checking", "--apply"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '2026-03-01 ! "Coffee"' in (tmp_path / "main.bean").read_text()
