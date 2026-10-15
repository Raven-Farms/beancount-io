"""A `--rules` pattern with a POSIX class is refused in bea's words (w5/427).

Python reads `[[:alpha:]]` as a set of characters and only warns, so the raw
`FutureWarning`, with bea's source path, reached stderr and the rule matched
nothing: its rows fell to Expenses:Uncategorized with exit 0.
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
2026-01-01 open Expenses:Uncategorized USD
"""


def _import(books: Path, match: str) -> subprocess.CompletedProcess[str]:
    (books / "main.bean").write_text(LEDGER)
    (books / "s.csv").write_text("Date,Payee,Amount\n2026-01-05,Shop,-5.00\n")
    (books / "r.toml").write_text(f"[[rule]]\nmatch = '{match}'\naccount = \"Expenses:Food\"\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "PYTHONWARNINGS"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "import", "s.csv"]
        + ["--account", "Assets:Cash", "--csv", "date=Date,payee=Payee,amount=Amount", "--rules", "r.toml"],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_a_posix_class_rule_is_refused(tmp_path: Path) -> None:
    result = _import(tmp_path, "[[:alpha:]]")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "Rule 1 match '[[:alpha:]]': [:alpha:] is a POSIX class" in result.stderr
    assert "[^\\W\\d_]" in result.stderr
    assert "FutureWarning" not in result.stderr


@pytest.mark.parametrize("match", ["\\w+", "[a-z]"])
def test_ordinary_rules_still_categorize(tmp_path: Path, match: str) -> None:
    result = _import(tmp_path, match)
    assert result.returncode == 0, result.stderr
    assert "Expenses:Food   5.00 USD" in result.stdout
    assert "FutureWarning" not in result.stderr
