"""A fresh `bea init` ledger takes a foreign charge on a category (w5/363).

`init` limited all 14 starter accounts, categories included, to the one
operating currency, so `Expenses:Dining 45 EUR @ 1.10 USD` was refused with
Beancount's bare `Invalid currency EUR for account 'Expenses:Dining'`, and
`bea add open` could not widen the open. Categories are now unrestricted,
and a refusal on an account that is still restricted names its open line and
the two remedies.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _init(tmp_path: Path) -> Path:
    result = _bea(tmp_path, "--no-input", "init", "books", "--currency", "USD", "--date", "2026-01-01")
    assert result.returncode == 0, result.stderr
    return tmp_path / "books" / "main.bean"


def test_a_foreign_charge_on_a_starter_category_is_written(tmp_path: Path) -> None:
    ledger = _init(tmp_path)
    text = ledger.read_text()
    assert "2026-01-01 open Expenses:Dining\n" in text
    assert "2026-01-01 open Assets:Checking USD\n" in text
    assert "2026-01-01 open Liabilities:CreditCard USD\n" in text

    added = _bea(
        tmp_path,
        *("--file", str(ledger), "add", "transaction", "--date", "2026-03-02", "--payee", "CAFE"),
        *("--narration", "lunch", "-p", "Expenses:Dining 45 EUR @ 1.10 USD", "-p", "Liabilities:CreditCard"),
    )

    assert added.returncode == 0, added.stderr
    assert "45 EUR @ 1.10 USD" in ledger.read_text()
    assert _bea(tmp_path, "--file", str(ledger), "check").returncode == 0
    assert _bea(tmp_path, "--file", str(ledger), "format", "--check").returncode == 0


def test_a_currency_the_open_refuses_names_that_open_and_the_remedies(tmp_path: Path) -> None:
    ledger = _init(tmp_path)
    before = ledger.read_bytes()
    line = next(n for n, text in enumerate(before.decode().splitlines(), 1) if "open Liabilities:CreditCard" in text)

    refused = _bea(
        tmp_path,
        *("--file", str(ledger), "add", "transaction", "--date", "2026-03-02", "--payee", "CAFE"),
        *("--narration", "lunch", "-p", "Expenses:Dining 49.50 USD", "-p", "Liabilities:CreditCard -45 EUR @ 1.10 USD"),
    )

    assert refused.returncode == 1, refused.stdout
    assert ledger.read_bytes() == before
    assert f"Liabilities:CreditCard is opened at {ledger}:{line} for USD only." in refused.stderr
    assert "'2026-01-01 open Liabilities:CreditCard USD,EUR'" in refused.stderr
    assert "otherwise record this posting in USD" in refused.stderr
