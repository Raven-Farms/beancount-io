"""`bea format -i` keeps a lone CR inside a comment or a string (w5/355).

The formatter normalized `\\r` to `\\n` as well as `\\r\\n`, so a comment's tail
became a line of its own (a syntax error) and a payee changed value, while
`format -i` reported success.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n'
    "2020-01-01 open Assets:Cash USD\n"
    "2020-01-01 open Equity:O\n"
    '2020-01-02 * "Shop" "memo"\n'
    "  Assets:Cash   5 USD ; old\rEquity:O -5 USD\n"
    "  Equity:O\n"
    '2020-01-03 * "pay\ree" "x"\n'
    "  Assets:Cash   1 USD\n"
    "  Equity:O\n"
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_format_in_place_keeps_the_comment_and_the_payee(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(LEDGER.encode())
    assert _bea(tmp_path, "-f", str(ledger), "check").returncode == 0
    assert _bea(tmp_path, "format", "-i", str(ledger)).returncode == 0
    assert _bea(tmp_path, "-f", str(ledger), "check").returncode == 0
    assert b"; old\rEquity:O -5 USD" in ledger.read_bytes()
    listed = _bea(tmp_path, "--json", "-f", str(ledger), "list", "transaction")
    assert "pay\ree" in [row["payee"] for row in json.loads(listed.stdout)["data"]]


def test_crlf_still_converts(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(b'option "operating_currency" "USD"\r\n2020-01-01 open Assets:Cash USD\r\n')
    assert _bea(tmp_path, "format", "-i", str(ledger)).returncode == 0
    assert b"\r" not in ledger.read_bytes()
