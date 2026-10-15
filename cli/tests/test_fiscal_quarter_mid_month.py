"""A fiscal quarter on a fiscal year that starts mid-month is refused with the real reason (w5/329).

Fava defines no quarters then. `fiscal_quarter` said so, but the explicit
`FY2027-Q2` came back as `Failed to parse date`, blaming the spelling.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Checking USD
2024-01-01 open Equity:Opening
2024-01-01 custom "fava-option" "fiscal-year-end" "{end}"
"""


def _bea(tmp_path: Path, end: str, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER.format(end=end))
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    "args",
    [
        ("report", "income-statement", "-t", "FY2027-Q2"),
        ("report", "income-statement", "-t", "fiscal_quarter"),
        ("balance", "-t", "FY2027-Q2"),
    ],
    ids=["explicit", "relative", "balance"],
)
def test_every_quarter_spelling_names_the_rule(tmp_path: Path, args: tuple[str, ...]) -> None:
    result = _bea(tmp_path, "04-05", *args)
    message = " ".join(result.stderr.split())
    assert result.returncode == 2, result.stderr
    assert "fiscal year ends on 04-05" in message and "main.bean:4" in message
    assert "does not start on the first of a month" in message
    assert "Failed to parse date" not in message


def test_the_whole_fiscal_year_and_first_of_month_quarters_still_report(tmp_path: Path) -> None:
    assert _bea(tmp_path, "04-05", "report", "income-statement", "-t", "FY2027").returncode == 0
    assert _bea(tmp_path, "03-31", "report", "income-statement", "-t", "FY2028-Q1").returncode == 0
