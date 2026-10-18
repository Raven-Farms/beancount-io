"""`add transaction` names the posting that holds a syntax error (w5/486).

Beancount reports an "unexpected EOL" on the line after the one missing its
token, so the blame moved one posting down, or off the last posting onto the
transaction header. A U+2028 in the narration shifted it too, as the header's
lines were counted with `str.splitlines`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash\n2026-01-01 open Assets:Brokerage\n'
UNCLOSED = "Assets:Brokerage 2 HOOL {10 USD"


@pytest.mark.parametrize(
    ("narration", "postings", "blamed"),
    [
        ("ab", ("Assets:Cash -20 USD", UNCLOSED), "--posting 2"),
        ("ab", (UNCLOSED, "Assets:Cash -20 USD"), "--posting 1"),
        ("ab", ("Assets:Cash -20 USD", UNCLOSED, "Assets:Cash"), "--posting 2"),
        ("a b", ("Assets:Cash 1 USD }", "Assets:Brokerage"), "--posting 1"),
        ("a b", ("Assets:Cash -20 USD", UNCLOSED), "--posting 2"),
    ],
    ids=["last", "first", "middle-of-three", "line-separator", "paragraph-separator"],
)
def test_the_posting_holding_the_error_is_named(
    tmp_path: Path, narration: str, postings: tuple[str, ...], blamed: str
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    flags = [arg for posting in postings for arg in ("-p", posting)]
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(ledger), "add", "transaction", narration, "--date", "2026-01-05"]
        + flags,
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"  {blamed}: syntax error" in result.stderr
    assert "Transaction options:" not in result.stderr
    assert "Invalid transaction header" not in result.stderr
    assert ledger.read_text() == LEDGER
