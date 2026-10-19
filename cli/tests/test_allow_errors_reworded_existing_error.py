"""`--allow-errors` tolerates an existing error the write only rewords (w5/150).

Some loader messages describe the books around an entry rather than the entry:
a booking failure lists the account's lots, an unbalanced sale its residual. A
backdated purchase changes that text without causing the error, and keyed on
the message the same failure on the same line read as newly introduced — so a
sale entered before its purchases could never be backfilled one at a time.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

HEADER = """option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Assets:Broker "{booking}"
2024-01-01 open Assets:Other "STRICT"
2024-01-01 open Income:Gains
2024-01-01 open Equity:Opening

2024-01-02 * "Opening"
  Assets:Cash  100000.00 USD
  Equity:Opening

2024-02-01 * "other buy"
  Assets:Other  10 ZED {{20 USD}}
  Assets:Cash

2024-02-02 * "other sell"
  Assets:Other  -5 ZED {{}} @ 30 USD
  Assets:Cash  150 USD
  Income:Gains

"""

BUY = """2024-02-01 * "buy 1"
  Assets:Broker  10 ACME {100 USD}
  Assets:Cash

"""

SECOND_BUY = """2024-02-05 * "buy 2"
  Assets:Broker  10 ACME {105 USD}
  Assets:Cash

"""

SHORT_SALE = """2024-03-01 * "sell"
  Assets:Broker  -30 ACME {} @ 150 USD
  Assets:Cash  4500 USD
  Income:Gains
"""

SMALL_SALE = """2024-03-01 * "sell"
  Assets:Broker  -5 ACME {} @ 150 USD
  Assets:Cash  750 USD
  Income:Gains
"""

UNBALANCED_SALE = """2024-03-01 * "sell"
  Assets:Broker  -10 ACME {}
  Assets:Cash  1100 USD
"""

# (ledger body, text of the error before the write, text of the same error after it)
VARIANTS = [
    pytest.param(
        HEADER.format(booking="FIFO") + BUY + SHORT_SALE,
        "Not enough lots to reduce",
        "10 ACME {90 USD, 2024-01-15}",
        id="not-enough-lots",
    ),
    pytest.param(
        HEADER.format(booking="STRICT") + BUY + SECOND_BUY + SMALL_SALE,
        "Ambiguous matches",
        "10 ACME {90 USD, 2024-01-15}",
        id="ambiguous-matches",
    ),
    pytest.param(
        HEADER.format(booking="FIFO") + SHORT_SALE,
        "Too many missing numbers",
        "Not enough lots to reduce",
        id="missing-numbers-becomes-not-enough-lots",
    ),
    pytest.param(
        HEADER.format(booking="FIFO") + BUY + UNBALANCED_SALE,
        "Transaction does not balance: (100 USD)",
        "Transaction does not balance: (200 USD)",
        id="residual",
    ),
]


def _bea(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
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
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _ledger(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(body, encoding="utf-8")
    return path


def _sale_line(body: str) -> int:
    return body.splitlines().index('2024-03-01 * "sell"') + 1


def _buy(tmp_path: Path, ledger: Path, date: str, *postings: str) -> subprocess.CompletedProcess[str]:
    args = ["--file", str(ledger), "add", "transaction", "backfill", "--date", date, "--allow-errors"]
    for posting in postings:
        args += ["--posting", posting]
    return _bea(tmp_path, *args)


@pytest.mark.parametrize(("body", "before", "after"), VARIANTS)
def test_a_backdated_purchase_keeps_the_existing_error_a_warning(
    tmp_path: Path, body: str, before: str, after: str
) -> None:
    ledger = _ledger(tmp_path, body)
    checked = _bea(tmp_path, "--file", str(ledger), "check")
    assert checked.returncode == 1
    assert before in checked.stderr
    assert after not in checked.stderr or after == before

    done = _buy(tmp_path, ledger, "2024-01-15", "Assets:Broker 10 ACME {90 USD}", "Assets:Cash")

    assert done.returncode == 0, done.stderr
    assert f"{ledger}:{_sale_line(body)}: " in done.stderr
    assert after in done.stderr
    assert "new ledger error" not in done.stderr
    assert ledger.read_text().startswith(body)
    assert '2024-01-15 * "backfill"' in ledger.read_text()[len(body) :]


@pytest.mark.parametrize(("body", "before", "after"), VARIANTS)
def test_the_bulk_form_tolerates_the_same_reworded_error(tmp_path: Path, body: str, before: str, after: str) -> None:
    ledger = _ledger(tmp_path, body)
    rows = [
        {
            "date": "2024-01-15",
            "narration": "backfill",
            "postings": [
                {
                    "account": "Assets:Broker",
                    "units": {"number": "10", "currency": "ACME"},
                    "cost": {"number": "90", "currency": "USD"},
                },
                {"account": "Assets:Cash"},
            ],
        }
    ]

    done = _bea(
        tmp_path, "--file", str(ledger), "add", "transactions", "--from", "-", "--allow-errors", stdin=json.dumps(rows)
    )

    assert done.returncode == 0, done.stderr
    assert after in done.stderr
    assert '2024-01-15 * "backfill"' in ledger.read_text()[len(body) :]


def test_a_purchase_dated_after_the_sale_is_the_unchanged_control(tmp_path: Path) -> None:
    body = HEADER.format(booking="FIFO") + BUY + SHORT_SALE
    ledger = _ledger(tmp_path, body)

    done = _buy(tmp_path, ledger, "2024-03-02", "Assets:Broker 10 ACME {90 USD}", "Assets:Cash")

    assert done.returncode == 0, done.stderr
    assert 'Not enough lots to reduce "-30 ACME {}": 10 ACME {100 USD, 2024-02-01}\n' in done.stderr


def test_an_error_on_the_appended_entry_is_still_refused(tmp_path: Path) -> None:
    body = HEADER.format(booking="FIFO") + BUY + SHORT_SALE
    ledger = _ledger(tmp_path, body)

    done = _buy(tmp_path, ledger, "2024-01-15", "Assets:Broker 10 ACME {90 USD}", "Assets:Nope")

    assert done.returncode == 1, done.stdout
    assert "1 new ledger error" in done.stderr
    assert "Assets:Nope" in done.stderr
    assert "Not enough lots" not in done.stderr, "the reworded existing error is not what blocked the write"
    assert ledger.read_text() == body


def test_breaking_a_different_existing_entry_is_still_refused(tmp_path: Path) -> None:
    """Same kind of error, another line: the anchor is the line, not the class alone."""
    body = HEADER.format(booking="STRICT") + BUY + SECOND_BUY + SMALL_SALE
    ledger = _ledger(tmp_path, body)
    other_sale = body.splitlines().index('2024-02-02 * "other sell"') + 1

    done = _buy(tmp_path, ledger, "2024-01-15", "Assets:Other 10 ZED {25 USD}", "Assets:Cash")

    assert done.returncode == 1, done.stdout
    assert "1 new ledger error" in done.stderr
    assert f"{ledger}:{other_sale}: Ambiguous matches" in done.stderr
    assert f"{ledger}:{_sale_line(body)}: " not in done.stderr
    assert ledger.read_text() == body


def test_a_second_error_on_the_same_line_is_still_refused(tmp_path: Path) -> None:
    """One existing error on a line tolerates one error there, not two."""
    body = HEADER.format(booking="FIFO") + BUY + UNBALANCED_SALE
    ledger = _ledger(tmp_path, body)

    done = _bea(
        tmp_path, "--file", str(ledger), "add", "close", "--account", "Assets:Cash", "--date", "2024-02-15", "--force",
        "--allow-errors",
    )  # fmt: skip

    assert done.returncode == 1, done.stdout
    assert "new ledger error" in done.stderr
    assert "inactive account 'Assets:Cash'" in done.stderr
    assert ledger.read_text() == body
