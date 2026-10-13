"""`--allow-errors` tolerates an account-level plugin error the append re-anchors (w5/153).

`onecommodity` reports an account's violation at the account's latest posting,
and `check_commodity` reports against no line while naming the first account
that uses the currency. A new transaction can therefore move the line or the
wording of an error the books already had; keyed on file, line and message it
read as introduced by the write and refused every such append.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ONE_COMMODITY = """plugin "beancount.plugins.onecommodity"
option "operating_currency" "USD"
2023-01-01 open Assets:Bank USD
2023-01-01 open Assets:Cash
2023-01-01 open Equity:Opening USD
2023-01-01 open Expenses:Food
2023-01-01 open Expenses:Rent

2023-01-02 * "Opening"
  Assets:Bank  1000.00 USD
  Equity:Opening

2023-02-01 * "Lunch"
  Expenses:Food  10.00 USD
  Assets:Bank

2023-02-05 * "Trip lunch"
  Expenses:Food  5.00 EUR
  Assets:Cash
"""

CHECK_COMMODITY = """plugin "beancount.plugins.check_commodity"
2023-01-01 open Assets:Bank
2023-01-01 open Assets:Aaa
2023-01-01 open Equity:Opening

2023-01-02 * "Opening"
  Assets:Bank  1000.00 USD
  Equity:Opening
"""


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
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _ledger(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(text, encoding="utf-8")
    return path


def _add(tmp_path: Path, ledger: Path, *postings: str) -> subprocess.CompletedProcess[str]:
    args = [arg for posting in postings for arg in ("--posting", posting)]
    return _bea(
        tmp_path, "--file", str(ledger), "add", "transaction", "--allow-errors", "--date", "2023-03-01", "Dinner", *args
    )


def _errors(tmp_path: Path, ledger: Path) -> list[str]:
    done = _bea(tmp_path, "--file", str(ledger), "check")
    return [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]


def test_a_later_posting_to_the_violating_account_is_tolerated(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, ONE_COMMODITY)
    assert len(_errors(tmp_path, ledger)) == 1, "the ledger starts with one error"

    done = _add(tmp_path, ledger, "Expenses:Food 20.00 USD", "Assets:Bank")

    assert done.returncode == 0, done.stderr
    assert "More than one currency in account 'Expenses:Food'" in done.stdout + done.stderr
    assert '2023-03-01 * "Dinner"' in ledger.read_text()
    after = _errors(tmp_path, ledger)
    assert len(after) == 1 and "'Expenses:Food'" in after[0], after


def test_a_posting_elsewhere_still_repeats_the_existing_error(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, ONE_COMMODITY)

    done = _add(tmp_path, ledger, "Expenses:Rent 20.00 USD", "Assets:Bank")

    assert done.returncode == 0, done.stderr
    assert "main.bean:17: More than one currency in account 'Expenses:Food'" in done.stdout + done.stderr
    assert '2023-03-01 * "Dinner"' in ledger.read_text()


def test_a_second_multi_currency_account_is_still_refused(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, ONE_COMMODITY)
    before = ledger.read_bytes()

    done = _add(
        tmp_path,
        ledger,
        "Expenses:Rent 20.00 EUR",
        "Expenses:Rent 20.00 USD",
        "Assets:Cash -20.00 EUR",
        "Assets:Bank -20.00 USD",
    )

    assert done.returncode == 1, done.stdout
    assert "1 new ledger error" in done.stderr
    assert "'Expenses:Rent'" in done.stderr and "'Expenses:Food'" not in done.stderr
    assert ledger.read_bytes() == before


def test_a_missing_commodity_error_that_names_another_account_is_tolerated(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, CHECK_COMMODITY)
    assert _errors(tmp_path, ledger) == ["<check_commodity>:0: Missing Commodity directive for 'USD' in 'Assets:Bank'"]

    done = _add(tmp_path, ledger, "Assets:Aaa 20.00 USD", "Assets:Bank")

    assert done.returncode == 0, done.stderr
    assert "Missing Commodity directive for 'USD' in 'Assets:Aaa'" in done.stdout + done.stderr
    assert '2023-03-01 * "Dinner"' in ledger.read_text()
    assert len(_errors(tmp_path, ledger)) == 1


def test_a_second_missing_commodity_is_still_refused(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, CHECK_COMMODITY)
    before = ledger.read_bytes()

    done = _add(tmp_path, ledger, "Assets:Aaa 20.00 GBP", "Assets:Bank")

    assert done.returncode == 1, done.stdout
    assert "1 new ledger error" in done.stderr
    assert "'GBP'" in done.stderr and "'USD'" not in done.stderr
    assert ledger.read_bytes() == before
