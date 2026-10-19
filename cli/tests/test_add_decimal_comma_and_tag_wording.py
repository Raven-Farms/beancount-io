"""A decimal comma in a posting or balance gets the shared message; tags say ASCII letters (w5/534).

Postings and balances relayed Beancount's `ValueError: Invalid number
format: '4,50'`, though `add price` explains a decimal comma, and the tag
refusal said "letters" for a grammar that takes ASCII only. The European
`1.234,56` and bulk `amount` strings took the same raw path, and the shared
tag-or-link refusal named both sigils while quoting the stripped value
(w5/722).
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


@pytest.mark.parametrize(
    "args",
    [
        ("transaction", "--date", "2026-02-01", "-p", "Expenses:Food 1.234,56 EUR", "-p", "Assets:Checking"),
        ("balance", "--date", "2026-02-01", "-a", "Assets:Checking", "--amount", "1.234,56 EUR"),
    ],
    ids=["posting", "balance"],
)
def test_a_european_decimal_comma_gets_the_shared_message(tmp_path: Path, args: tuple[str, ...]) -> None:
    result = _add(tmp_path, *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"Invalid amount '1.234,56'. {COMMA}" in result.stderr
    assert "unexpected COMMA" not in result.stderr


def test_a_bulk_amount_comma_gets_the_shared_message(tmp_path: Path) -> None:
    rows = tmp_path / "rows.json"
    rows.write_text(
        '[{"date": "2026-02-01", "narration": "b", "postings": '
        '[{"account": "Expenses:Food", "amount": "4,50 EUR"}, {"account": "Assets:Checking"}]}]'
    )
    result = _add(tmp_path, "transactions", "--from", str(rows))

    assert result.returncode == 1, result.stdout + result.stderr
    assert (
        f"Row 1, postings.0: Value error, Could not parse amount '4,50 EUR' as a posting fragment: "
        f"Invalid amount '4,50'. {COMMA}" in result.stderr
    )
    assert "Invalid number format" not in result.stderr


def test_a_bulk_amount_exponent_gets_the_shared_message(tmp_path: Path) -> None:
    rows = tmp_path / "rows.json"
    rows.write_text(
        '[{"date": "2026-02-01", "narration": "b", "postings": '
        '[{"account": "Expenses:Food", "amount": "5 HOOL {1e2 USD}"}, {"account": "Assets:Checking"}]}]'
    )
    result = _add(tmp_path, "transactions", "--from", str(rows))

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Row 1, postings.0: Value error, Scientific notation '1e2' is not supported" in result.stderr
    assert "Invalid token" not in result.stderr


@pytest.mark.parametrize(
    ("flag", "value", "noun", "sigil"),
    [
        ("--tag", "^a2", "tag", "#"),
        ("--tag", "##c", "tag", "#"),
        ("--link", "#x", "link", "^"),
    ],
    ids=["tag-wrong-sigil", "tag-doubled-sigil", "link-wrong-sigil"],
)
def test_a_tag_or_link_refusal_names_its_own_sigil_and_quotes_the_typed_value(
    tmp_path: Path, flag: str, value: str, noun: str, sigil: str
) -> None:
    result = _add(
        tmp_path,
        "transaction",
        "--date",
        "2026-02-01",
        flag,
        value,
        "-p",
        "Expenses:Food 4 EUR",
        "-p",
        "Assets:Checking",
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"{value!r} is not one {noun}; use only ASCII letters, digits" in result.stderr
    assert f"after an optional leading {sigil}" in result.stderr
    assert "# or ^" not in result.stderr


def test_a_bulk_link_refusal_names_the_link_sigil(tmp_path: Path) -> None:
    rows = tmp_path / "rows.json"
    rows.write_text(
        '[{"date": "2026-02-01", "narration": "b", "links": ["#x"], "postings": '
        '[{"account": "Expenses:Food", "amount": "1 EUR"}, {"account": "Assets:Checking"}]}]'
    )
    result = _add(tmp_path, "transactions", "--from", str(rows))

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Row 1, links.0: Value error, '#x' is not one link" in result.stderr
    assert "after an optional leading ^" in result.stderr
