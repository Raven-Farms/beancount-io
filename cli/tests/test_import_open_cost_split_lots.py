"""An open-cost sale that booking splits across lots is matched to its booked twin (w5/603).

w5/467 made `{}` compare only the cost fields it states, but the legs still
had to match one to one. When booking reduces two lots the ledger holds two
postings, so re-importing bea's own write of `-20 HOOL {}` was a conflict
(exit 4), and a hand-entered FIFO sale was written a second time, exit 0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HEADER = """option "operating_currency" "USD"
{options}2026-01-01 open Assets:Broker:Cash USD
2026-01-01 open Assets:Broker:HOOL HOOL
2026-01-01 open Income:Gains USD
2026-01-01 commodity HOOL
"""
BUY = """
{date} * "buy"
  Assets:Broker:HOOL  10 HOOL {{{cost} USD}}
  Assets:Broker:Cash  -{total} USD
"""
#: Entered by hand: FIFO books it as 10 from the 150 USD lot and 5 from the 155 USD lot.
FIFO_SALE = """
2026-02-01 * "sell"
  Assets:Broker:HOOL  -15 HOOL {} @ 160 USD
  Assets:Broker:Cash  2400 USD
  Income:Gains
"""
IMPORTER = """\
import datetime
import os
from decimal import Decimal
from beancount.core import amount, data, position
from beancount.core.number import MISSING


class Broker:
    name = "broker"

    def identify(self, filepath):
        return filepath.endswith(".txt")

    def account(self, filepath):
        return "Assets:Broker"

    def extract(self, filepath, existing):
        meta = data.new_metadata(filepath, 1)
        if os.environ.get("TEST_FITID"):
            meta["fitid"] = os.environ["TEST_FITID"]
        units = Decimal(os.environ["TEST_UNITS"])
        lot = position.CostSpec(MISSING, None, None, None, None, False)
        return [data.Transaction(meta, datetime.date(2026, 2, 1), "*", None, "sell", frozenset(), frozenset(), [
            data.Posting("Assets:Broker:HOOL", amount.Amount(-units, "HOOL"), lot,
                         amount.Amount(Decimal("160"), "USD"), None, None),
            data.Posting("Assets:Broker:Cash", amount.Amount(units * 160, "USD"), None, None, None, None),
            data.Posting("Income:Gains", None, None, None, None, None)])]


CONFIG = [Broker()]
"""


def _books(tmp_path: Path, lots: list[int], options: str = "", extra: str = "") -> Path:
    buys = "".join(
        BUY.format(date=f"2026-01-{10 + 5 * index:02d}", cost=cost, total=cost * 10) for index, cost in enumerate(lots)
    )
    (tmp_path / "main.bean").write_text(HEADER.format(options=options) + buys + extra)
    (tmp_path / "imp.py").write_text(IMPORTER)
    (tmp_path / "s.txt").write_text("statement\n")
    return tmp_path


def _import(books: Path, units: int, *flags: str, fitid: str = "") -> tuple[int, list[dict[str, Any]]]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        TEST_FITID=fitid,
        TEST_UNITS=str(units),
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--no-input", "-f", "main.bean"]
        + ["import", "s.txt", "--config", "imp.py", *flags],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    payload = json.loads(result.stdout or result.stderr)
    data = payload["data"] if "data" in payload else payload["error"]["result"]
    return result.returncode, list(data["rows"])


def test_re_importing_a_sale_booked_across_two_lots_is_an_exact_duplicate(tmp_path: Path) -> None:
    books = _books(tmp_path, [150, 155])
    code, rows = _import(books, 20, "--apply", fitid="SELL1")
    assert code == 0, rows
    written = (books / "main.bean").read_bytes()

    code, rows = _import(books, 20, "--apply", fitid="SELL1")

    assert code == 0, rows
    assert [row["status"] for row in rows] == ["duplicate"]
    assert (books / "main.bean").read_bytes() == written


def test_a_hand_entered_fifo_sale_across_lots_is_a_possible_duplicate(tmp_path: Path) -> None:
    books = _books(tmp_path, [150, 155, 158], options='option "booking_method" "FIFO"\n', extra=FIFO_SALE)
    before = (books / "main.bean").read_bytes()

    code, rows = _import(books, 15, "--apply")

    assert code == 4, rows
    assert [row["status"] for row in rows] == ["possible_duplicate"]
    assert (books / "main.bean").read_bytes() == before


def test_a_different_quantity_is_not_the_split_sale(tmp_path: Path) -> None:
    books = _books(tmp_path, [150, 155, 158], options='option "booking_method" "FIFO"\n', extra=FIFO_SALE)

    code, rows = _import(books, 12)

    assert code == 0, rows
    assert [row["status"] for row in rows] == ["new"]
