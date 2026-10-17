"""A decimal comma in a posting or balance gets the shared message; tags say ASCII letters (w5/534).

Postings and balances relayed Beancount's `ValueError: Invalid number
format: '4,50'`, though `add price` explains a decimal comma, and the tag
refusal said "letters" for a grammar that takes ASCII only.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "EUR"
2026-01-01 open Assets:Checking EUR
2026-01-01 open Expenses:Food EUR
"""
COMMA = "A comma is read only as a thousands separator between groups of three digits"


def _add(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "add", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    "args",
    [
        ("transaction", "--date", "2026-02-01", "-p", "Expenses:Food 4,50 EUR", "-p", "Assets:Checking"),
        ("balance", "--date", "2026-02-01", "-a", "Assets:Checking", "--amount", "4,50 EUR"),
    ],
    ids=["posting", "balance"],
)
def test_a_decimal_comma_gets_the_shared_message(tmp_path: Path, args: tuple[str, ...]) -> None:
    result = _add(tmp_path, *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"Invalid amount '4,50'. {COMMA}" in result.stderr
    assert "ValueError" not in result.stderr


def test_a_grouped_amount_still_writes(tmp_path: Path) -> None:
    result = _add(
        tmp_path, "transaction", "--date", "2026-02-01", "-p", "Expenses:Food 1,234.50 EUR", "-p", "Assets:Checking"
    )

    assert result.returncode == 0, result.stderr


def test_a_non_ascii_tag_is_told_ascii_letters(tmp_path: Path) -> None:
    result = _add(
        tmp_path,
        "transaction",
        "--date",
        "2026-02-01",
        "--tag",
        "café",
        "-p",
        "Expenses:Food 4 EUR",
        "-p",
        "Assets:Checking",
    )

    assert result.returncode == 2
    assert "use only ASCII letters, digits" in result.stderr
