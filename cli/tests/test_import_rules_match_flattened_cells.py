"""Import rules match the one-line text the preview shows, not the raw cell (w5/133).

`IMPORTING.md`: imported payees and narrations "replace CR/LF line breaks with
spaces before preview, duplicate matching, and writing." Rules were matched
before that flattening, so a quoted multi-line cell that displayed as
`CARD PURCHASE WHOLE FOODS MKT` did not match `purchase whole foods`, while the
same text typed on one line did, and a salary deposit was written against
`Expenses:Uncategorized`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Income:Salary
2026-01-01 open Expenses:Groceries
2026-01-01 open Expenses:Dining
2026-01-01 open Expenses:Uncategorized
"""

# Row 1 breaks its cell with LF, row 3 with CRLF; row 2 is the one-line control
# and row 4 matches no rule.
STATEMENT = (
    b"Date,Description,Amount\n"
    b'2026-08-02,"CARD PURCHASE\nWHOLE FOODS MKT",-20.00\n'
    b"2026-08-03,CARD PURCHASE WHOLE FOODS MKT,-21.00\n"
    b'2026-08-04,"ACME\r\nPAYROLL",1000.00\n'
    b'2026-08-05,"CORNER\nCAFE",-4.00\n'
)

RULES = """\
[[rule]]
match = "purchase whole foods"
account = "Expenses:Groceries"

[[rule]]
match = "^acme payroll$"
account = "Income:Salary"
"""

CATEGORY_STATEMENT = (
    b"Date,Description,Amount,Category\n"
    b'2026-08-06,LUNCH,-9.00,"Food &\r\nDrink"\n'
    b"2026-08-07,DINNER,-30.00,Food & Drink\n"
)

CATEGORY_RULES = """\
[[rule]]
match = "^food & drink$"
account = "Expenses:Dining"
"""


def _bea(tmp_path: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _counter_accounts(tmp_path: Path) -> dict[str, tuple[str, str]]:
    """Each imported entry's flag and counter account, keyed by its date."""
    rows = json.loads(
        _bea(
            tmp_path,
            "--json",
            "query",
            "SELECT date, flag, account WHERE account != 'Assets:Checking' ORDER BY date",
        )
    )["data"]["rows"]
    return {day: (flag, account) for day, flag, account in rows}


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    (tmp_path / "s.csv").write_bytes(STATEMENT)
    (tmp_path / "r.toml").write_text(RULES, encoding="utf-8")
    (tmp_path / "c.csv").write_bytes(CATEGORY_STATEMENT)
    (tmp_path / "c.toml").write_text(CATEGORY_RULES, encoding="utf-8")
    return tmp_path


def test_preview_names_the_rule_for_lf_and_crlf_cells(books: Path) -> None:
    out = _bea(books, "import", "s.csv", "--account", "Assets:Checking", "--rules", "r.toml")
    rules = {line.split()[0]: line for line in out.splitlines() if line[:1].isdigit()}

    assert "purchase whole foods" in rules["1"], out
    assert "purchase whole foods" in rules["2"], out
    assert "^acme payroll$" in rules["3"], out
    assert "unmatched" in rules["4"], out


def test_apply_posts_multiline_cells_to_the_rule_account(books: Path) -> None:
    _bea(books, "import", "s.csv", "--account", "Assets:Checking", "--rules", "r.toml", "--apply")

    assert _counter_accounts(books) == {
        "2026-08-02": ("*", "Expenses:Groceries"),
        "2026-08-03": ("*", "Expenses:Groceries"),
        "2026-08-04": ("*", "Income:Salary"),
        "2026-08-05": ("!", "Expenses:Uncategorized"),
    }
    # The written narration is the flattened text the rule was matched against.
    assert '2026-08-04 * "ACME PAYROLL"' in (books / "main.bean").read_text(encoding="utf-8")


def test_multiline_category_label_matches_like_its_one_line_twin(books: Path) -> None:
    _bea(
        books,
        "import",
        "c.csv",
        "--csv",
        "date=Date,amount=Amount,narration=Description,category=Category",
        "--account",
        "Assets:Checking",
        "--rules",
        "c.toml",
        "--apply",
    )

    assert _counter_accounts(books) == {
        "2026-08-06": ("*", "Expenses:Dining"),
        "2026-08-07": ("*", "Expenses:Dining"),
    }
