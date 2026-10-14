"""`format -c` overrides `-w`/`-W`, and the help says so (w5/242)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Checking USD
2024-01-01 open Equity:Opening USD
2024-01-02 * "Opening"
  Assets:Checking  1000.00 USD
  Equity:Opening
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _help_rows(tmp_path: Path) -> dict[str, str]:
    """Each option's help text keyed by its long flag, with wrapped lines rejoined."""
    shown = _bea(tmp_path, "format", "--help")
    assert shown.returncode == 0, shown.stderr or shown.stdout
    rows: dict[str, str] = {}
    flag = ""
    for line in shown.stdout.split("Options:", 1)[1].splitlines():
        words = line.split()
        if words and words[0].startswith("-"):
            flag = next(word for word in words if word.startswith("--"))
            rows[flag] = ""
        if flag:
            rows[flag] = f"{rows[flag]} {' '.join(words)}".strip()
    return rows


@pytest.mark.parametrize("flag", ["--prefix-width", "--num-width"])
def test_width_help_says_the_currency_column_overrides_it(tmp_path: Path, flag: str) -> None:
    assert "ignored with -c" in _help_rows(tmp_path)[flag]


def test_currency_column_help_names_the_widths_it_overrides(tmp_path: Path) -> None:
    assert "overrides -w and -W" in _help_rows(tmp_path)["--currency-column"]


def test_usage_documents_the_interaction() -> None:
    prose = " ".join((ROOT / "docs" / "USAGE.md").read_text(encoding="utf-8").split())
    assert "`--prefix-width` and `--num-width` given beside it are accepted and have no effect" in prose


def test_the_documented_interaction_is_what_format_does(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    def formatted(*alignment: str) -> str:
        result = _bea(tmp_path, "format", *alignment, str(ledger))
        assert result.returncode == 0, result.stderr or result.stdout
        return result.stdout

    column = formatted("-c", "60")
    assert formatted("-c", "60", "-w", "40", "-W", "20") == column
    # Control: the widths do work on their own, and beside a zero column,
    # which keeps automatic sizing rather than selecting a column.
    widths = formatted("-w", "40", "-W", "20")
    assert widths != column
    assert widths != formatted()
    assert formatted("-c", "0", "-w", "40", "-W", "20") == widths
