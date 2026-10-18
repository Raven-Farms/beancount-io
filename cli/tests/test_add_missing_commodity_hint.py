"""`add` refused by `check_commodity` labels its own currency and says how to declare it (w5/398).

The plugin reports against no ledger line (`<check_commodity>:0`), so the
refusal showed that pseudo-location with no `Proposed append` label and no
remedy, although CSV import already names `bea add commodity`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """plugin "beancount.plugins.check_commodity"
option "operating_currency" "USD"
2026-01-01 commodity USD
2026-01-01 open Assets:Cash
2026-01-01 open Expenses:Food
"""
PRICE = ("add", "price", "--date", "2026-01-05", "-c", "EUR", "--amount", "1.1 USD")
TRANSACTION = (
    "add",
    "transaction",
    "X",
    "--date",
    "2026-01-05",
    "-p",
    "Expenses:Food 5 EUR",
    "-p",
    "Assets:Cash -5 EUR",
)
# Named with its ledger since w5/619: `bea --file … add commodity …`.
REMEDY = "add commodity --date YYYY-MM-DD --currency EUR"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("command", [PRICE, TRANSACTION], ids=["price", "transaction"])
def test_undeclared_currency_is_the_proposed_append_with_a_remedy(tmp_path: Path, command: tuple[str, ...]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    before = ledger.read_bytes()
    result = _bea(tmp_path, "-f", str(ledger), *command)

    assert result.returncode == 1, result.stderr
    assert ledger.read_bytes() == before
    flat = " ".join(result.stderr.split())
    assert "Proposed append (not written): Missing Commodity directive for 'EUR'" in flat
    assert REMEDY in flat
    assert "<check_commodity>:0" not in flat


def test_json_refusal_carries_the_label_and_remedy(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    result = _bea(tmp_path, "--json", "-f", str(ledger), *PRICE)

    assert result.returncode == 1, result.stderr
    flat = json.dumps(json.loads(result.stdout or result.stderr))
    assert "Proposed append (not written): Missing Commodity directive for 'EUR'" in flat
    assert REMEDY in flat
    assert "<check_commodity>:0" not in flat


def test_declared_currency_still_writes(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + "2026-01-01 commodity EUR\n")
    result = _bea(tmp_path, "-f", str(ledger), *PRICE)

    assert result.returncode == 0, result.stderr
    assert "2026-01-05 price EUR" in ledger.read_text()


def test_a_currency_the_books_already_lacked_is_not_called_the_append(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + '2026-01-02 * "gbp"\n  Expenses:Food  5 GBP\n  Assets:Cash  -5 GBP\n')
    result = _bea(tmp_path, "-f", str(ledger), *TRANSACTION)

    assert result.returncode == 1, result.stderr
    flat = " ".join(result.stderr.split())
    assert "Proposed append (not written): Missing Commodity directive for 'EUR'" in flat
    assert "Proposed append (not written): Missing Commodity directive for 'GBP'" not in flat
    assert "Missing Commodity directive for 'GBP'" in flat
    assert "add commodity --date YYYY-MM-DD --currency GBP" in flat
    assert "<check_commodity>:0" not in flat
