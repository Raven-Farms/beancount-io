"""`query -o FILE.beancount` writes directives or nothing, never a text table (w5/459).

A SELECT to a ledger-named destination wrote the boxed text table there,
which fails to parse once a glob includes the file. `.tsv` and `.json`
destinations were already refused for the same reason.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Cafe" "Lunch"
  Expenses:Food  12.00 USD
  Assets:Cash   -12.00 USD
"""


def _query(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "query", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("name", ["p.beancount", "p.bean", "P.BEANCOUNT"])
def test_a_select_to_a_ledger_name_is_refused(tmp_path: Path, name: str) -> None:
    result = _query(tmp_path, "-o", str(tmp_path / name), "SELECT date, narration")
    assert result.returncode == 2, result.stderr
    assert "use PRINT" in result.stderr
    assert not (tmp_path / name).exists()


def test_print_to_a_ledger_name_writes_directives(tmp_path: Path) -> None:
    result = _query(tmp_path, "-o", str(tmp_path / "p.beancount"), "PRINT FROM year = 2026")
    assert result.returncode == 0, result.stderr
    assert '2026-01-05 * "Cafe" "Lunch"' in (tmp_path / "p.beancount").read_text()


def test_an_explicit_text_format_is_still_honoured(tmp_path: Path) -> None:
    result = _query(tmp_path, "-o", str(tmp_path / "p.beancount"), "--format", "text", "SELECT date")
    assert result.returncode == 0, result.stderr
    assert "2026-01-05" in (tmp_path / "p.beancount").read_text()
