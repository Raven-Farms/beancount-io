"""A repeated `sign=` in `--csv` is refused like every other repeated key (w5/426).

`sign` was assigned before the duplicate check, so the last value silently
won: `sign=ledger,sign=bank` and `sign=bank,sign=ledger` booked opposite
signs, both with exit 0.
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
2026-01-01 open Expenses:Uncategorized USD
"""
MAPPING = "date=Date,payee=Payee,amount=Amount"


def _import(books: Path, spec: str) -> subprocess.CompletedProcess[str]:
    (books / "main.bean").write_text(LEDGER)
    (books / "s.csv").write_text("Date,Payee,Amount\n2026-01-05,Shop,-5.00\n")
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
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "import", "s.csv"]
        + ["--account", "Assets:Cash", "--csv", spec, "--apply"],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("signs", ["sign=ledger,sign=bank", "sign=bank,sign=ledger", "sign=bank,sign=bank"])
def test_a_repeated_sign_is_refused(tmp_path: Path, signs: str) -> None:
    result = _import(tmp_path, f"{MAPPING},{signs}")
    assert result.returncode == 2, result.stderr
    assert "Duplicate --csv field 'sign'." in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


@pytest.mark.parametrize(("sign", "cash"), [("sign=bank", "-5.00 USD"), ("sign=ledger", "5.00 USD")])
def test_a_single_sign_still_applies(tmp_path: Path, sign: str, cash: str) -> None:
    result = _import(tmp_path, f"{MAPPING},{sign}")
    assert result.returncode == 0, result.stderr
    assert "Assets:Cash" in (tmp_path / "main.bean").read_text()
    assert any(
        line.split() == ["Assets:Cash", *cash.split()] for line in (tmp_path / "main.bean").read_text().splitlines()
    )
