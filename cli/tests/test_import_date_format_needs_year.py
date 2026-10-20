"""`import --date-format` without a year directive is refused (w5/783).

`strptime` defaults a missing year to 1900, so `%d/%m` booked every row in
1900 — blocked behind "Re-date that open to 1900", or silently `new` on a
ledger old enough. A format with no `%Y`, `%y` or `%G` now exits 2 before
any row is read.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n2020-01-01 open Assets:Cash USD\n2020-01-01 open Expenses:Uncategorized USD\n'
)
MAPPING = "date=Date,amount=Amount,narration=Description"


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
        [sys.executable, "-m", "cli.main", "-f", "main.bean", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "noyear.csv").write_text("Date,Amount,Description\n05/03,-10.00,A\n")
    (tmp_path / "full.csv").write_text("Date,Amount,Description\n05/03/2026,-10.00,A\n")
    (tmp_path / "short.csv").write_text("Date,Amount,Description\n05/03/26,-10.00,A\n")
    return tmp_path


@pytest.mark.parametrize("value", ["%d/%m", "%d/%%Y/%m"])
def test_a_format_without_a_year_is_refused(books: Path, value: str) -> None:
    result = _bea(books, "import", "noyear.csv", "--csv", MAPPING, "--account", "Assets:Cash", "--date-format", value)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"--date-format {value!r} has no year directive" in result.stderr
    assert "1900" in result.stderr


@pytest.mark.parametrize(
    ("source", "value", "shown"),
    [("full.csv", "%d/%m/%Y", "2026-03-05"), ("short.csv", "%d/%m/%y", "2026-03-05")],
)
def test_year_directives_keep_working(books: Path, source: str, value: str, shown: str) -> None:
    result = _bea(books, "import", source, "--csv", MAPPING, "--account", "Assets:Cash", "--date-format", value)

    assert result.returncode == 0, result.stderr
    assert shown in result.stdout
