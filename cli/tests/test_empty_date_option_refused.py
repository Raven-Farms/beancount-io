"""An empty optional date is refused, not replaced by the default (w5/239).

`--date "$D"` with `D` unset reaches the command as `""`. `add transaction`,
`add balance --pad-date` and `init --date` tested the value for truthiness, so
the empty string was treated as "option omitted": the entry was booked on
today's date (or the default pad date) with exit 0. Only an omitted option
takes the documented default.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Checking USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Equity:Opening USD
2024-01-02 * "Opening"
  Assets:Checking  1000.00 USD
  Equity:Opening
"""
TRANSACTION = ["add", "transaction", "Coffee", "-p", "Expenses:Food 5.00 USD", "-p", "Assets:Checking"]
PADDED = ["add", "balance", "--date", "2024-02-01", "-a", "Assets:Checking"]
PADDED += ["--amount", "900.00 USD", "--pad-from", "Equity:Opening"]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
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
        timeout=120,
    )


def _today_during(run: subprocess.CompletedProcess[str], before: datetime.date) -> set[str]:
    """The dates "today" could have been while `run` executed (it may straddle midnight)."""
    assert run.returncode == 0, run.stderr
    return {before.isoformat(), datetime.date.today().isoformat()}


@pytest.mark.parametrize(
    "args",
    [[*TRANSACTION, "--date", ""], [*PADDED, "--pad-date", ""]],
    ids=["transaction-date", "balance-pad-date"],
)
def test_an_empty_add_date_is_refused_and_writes_nothing(tmp_path: Path, args: list[str]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")

    result = _bea(tmp_path, "--file", str(ledger), *args)

    assert result.returncode == 2, result.stdout
    assert "Invalid date ''" in result.stderr
    assert ledger.read_text(encoding="utf-8") == LEDGER


def test_an_empty_init_date_is_refused_and_creates_nothing(tmp_path: Path) -> None:
    ledger = tmp_path / "books" / "main.bean"

    result = _bea(tmp_path, "--no-input", "init", str(ledger), "--currency", "USD", "--date", "")

    assert result.returncode == 2, result.stdout
    assert "Invalid date ''" in result.stderr
    assert not ledger.exists()


def test_an_omitted_transaction_date_still_defaults_to_today(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    before = datetime.date.today()

    result = _bea(tmp_path, "--file", str(ledger), *TRANSACTION)

    added = ledger.read_text(encoding="utf-8").removeprefix(LEDGER)
    assert any(f'{day} * "Coffee"' in added for day in _today_during(result, before)), added


def test_an_omitted_pad_date_still_defaults_to_the_day_before(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")

    result = _bea(tmp_path, "--file", str(ledger), *PADDED)

    assert result.returncode == 0, result.stderr
    added = ledger.read_text(encoding="utf-8").removeprefix(LEDGER)
    assert "2024-01-31 pad Assets:Checking Equity:Opening" in added
    assert "2024-02-01 balance Assets:Checking" in added


def test_an_omitted_init_date_still_defaults_to_today(tmp_path: Path) -> None:
    ledger = tmp_path / "books" / "main.bean"
    before = datetime.date.today()

    result = _bea(tmp_path, "--no-input", "init", str(ledger), "--currency", "USD")

    days = _today_during(result, before)
    created = ledger.read_text(encoding="utf-8")
    assert any(f"{day} open Assets:Checking" in created for day in days), created
