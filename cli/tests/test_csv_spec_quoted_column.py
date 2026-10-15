"""A `--csv` column whose name holds a comma can be double-quoted (w5/428).

The spec was split on every comma, quotes included, so a bank header such as
`Amount (USD, net)` could not be named at all: the error pointed at a
fragment, `Bad --csv mapping ' net)'`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Uncategorized USD
"""
CSV = 'Date,Payee,"Amount (USD, net)"\n2026-01-05,Shop,-5.00\n'


def _import(books: Path, spec: str, *extra: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "import", "c.csv"]
        + ["--account", "Assets:Cash", "--csv", spec, *extra],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "c.csv").write_text(CSV)
    return tmp_path


def test_a_quoted_column_maps_and_imports(tmp_path: Path) -> None:
    books = _books(tmp_path)
    result = _import(books, 'date=Date,payee=Payee,amount="Amount (USD, net)"', "--apply")
    assert result.returncode == 0, result.stderr
    assert "Assets:Cash             -5.00 USD" in (books / "main.bean").read_text()


def test_an_unquoted_comma_says_to_quote_the_column(tmp_path: Path) -> None:
    result = _import(_books(tmp_path), "date=Date,payee=Payee,amount=Amount (USD, net)")
    assert result.returncode == 2
    assert "Bad --csv mapping ' net)'" in result.stderr
    assert 'must be double-quoted, as in amount="Amount (USD, net)"' in result.stderr


def test_an_unclosed_quote_is_named(tmp_path: Path) -> None:
    result = _import(_books(tmp_path), 'date=Date,payee=Payee,amount="Amount (USD')
    assert result.returncode == 2
    assert "has an unclosed double quote" in result.stderr
