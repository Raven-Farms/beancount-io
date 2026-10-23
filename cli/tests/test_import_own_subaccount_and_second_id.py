"""Two re-imports w5/598 broke are exact duplicates again (w5/818).

w5/598 scoped an entry's bank ids to its first posting's account when that
is another balance-sheet account. That also caught a Python importer's own
entry whose first posting is a sub-account of its `account()` — a brokerage
trade listing `Assets:Broker:HOOL` first — and a migrated transfer's
`import-id-2`, which is by definition the second account's own id. Both
re-imports were held as "the other side of a transfer" (exit 4), and
`--duplicates include` booked them twice.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BROKER = """option "operating_currency" "USD"
2026-01-01 open Assets:Broker USD
2026-01-01 open Assets:Broker:HOOL HOOL
2026-01-01 open Expenses:Uncategorized USD
"""
IMPORTER = """\
import datetime
from decimal import Decimal
from beancount.core import amount, data


class Broker:
    name = "broker"

    def identify(self, filepath):
        return filepath.endswith(".ofx")

    def account(self, filepath):
        return "Assets:Broker"

    def extract(self, filepath, existing):
        meta = data.new_metadata(filepath, 1)
        meta["fitid"] = "B1"
        postings = [
            data.Posting("Assets:Broker:HOOL", amount.Amount(Decimal("10"), "HOOL"),
                         data.Cost(Decimal("50"), "USD", None, None), None, None, None),
            data.Posting("Assets:Broker", amount.Amount(Decimal("-500"), "USD"), None, None, None, None),
        ]
        return [data.Transaction(meta, datetime.date(2026, 3, 2), "*", None, "Buy HOOL",
                                 frozenset(), frozenset(), postings)]


CONFIG = [Broker()]
"""
MIGRATED = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Savings USD
2026-01-01 open Expenses:Uncategorized USD

2026-03-10 * "Transfer to savings"
  import-id: "bank:1001"
  import-id-2: "bank:2002"
  Assets:Checking  -500.00 USD
  Assets:Savings    500.00 USD
"""


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--no-input", "-f", str(books / "main.bean"), *args],
        cwd=books,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def _rows(result: subprocess.CompletedProcess[str]) -> list[dict[str, Any]]:
    payload = json.loads(result.stdout or result.stderr)
    data = payload["data"] if "data" in payload else payload["error"]["result"]
    return list(data["rows"])


def test_an_importers_own_trade_listing_a_sub_account_first_reimports_as_a_duplicate(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(BROKER)
    (tmp_path / "imp.py").write_text(IMPORTER)
    (tmp_path / "buy.ofx").write_text("statement\n")
    first = _bea(tmp_path, "import", "buy.ofx", "--config", "imp.py", "--apply")
    assert first.returncode == 0, first.stderr
    written = (tmp_path / "main.bean").read_bytes()

    again = _bea(tmp_path, "import", "buy.ofx", "--config", "imp.py", "--apply")

    assert again.returncode == 0, again.stderr
    (row,) = _rows(again)
    assert row["status"] == "duplicate", row
    assert row["reason"] == "import-id ofx:B1 is already in the ledger."
    assert (tmp_path / "main.bean").read_bytes() == written


def test_a_migrated_transfers_second_id_matches_the_second_accounts_row(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(MIGRATED)
    (tmp_path / "savings.csv").write_text("Date,Description,Amount,ID\n2026-03-10,TRANSFER FROM CHECKING,500.00,2002\n")

    result = _bea(
        tmp_path,
        "import",
        "savings.csv",
        "--csv",
        "date=Date,amount=Amount,narration=Description,id=ID",
        "--account",
        "Assets:Savings",
        "--apply",
    )

    assert result.returncode == 0, result.stderr
    (row,) = _rows(result)
    assert row["status"] == "duplicate", row
    assert "bank:2002" in row["reason"]
    assert (tmp_path / "main.bean").read_text() == MIGRATED


def test_the_first_accounts_id_still_matches_its_own_row(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(MIGRATED)
    (tmp_path / "checking.csv").write_text("Date,Description,Amount,ID\n2026-03-10,TRANSFER TO SAVINGS,-500.00,1001\n")

    result = _bea(
        tmp_path,
        "import",
        "checking.csv",
        "--csv",
        "date=Date,amount=Amount,narration=Description,id=ID",
        "--account",
        "Assets:Checking",
    )

    assert result.returncode == 0, result.stderr
    (row,) = _rows(result)
    assert row["status"] == "duplicate", row
