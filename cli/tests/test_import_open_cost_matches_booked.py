"""An importer's `{}` sale is the entry booking filled in as `{150 USD}` (w5/467).

Lots compared as text: the ledger's booked copy said `{150 USD}` and the
importer's open spec said nothing, so a hand-entered twin was written again,
a re-import under a native id was a conflict on bea's own write, and an id
written before lots were hashed stopped matching.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Broker:Cash USD
2026-01-01 open Assets:Broker:HOOL HOOL
2026-01-01 open Income:Gains USD
2026-01-01 commodity HOOL

2026-01-10 * "buy"
  Assets:Broker:HOOL  10 HOOL {150 USD}
  Assets:Broker:Cash  -1500 USD
"""
SALE = """
2026-02-01 * "sell"
{meta}  Assets:Broker:HOOL     -4 HOOL {{}} @ 160 USD
  Assets:Broker:Cash    640 USD
  Income:Gains
"""
# The units-only id releases before w5/349 wrote for this sale.
LEGACY_ID = '  import-id: "csv:sha256:4ecae98a24d049d0"\n'
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
        cost = os.environ.get("TEST_COST")
        lot = position.CostSpec(Decimal(cost) if cost else MISSING, None, "USD" if cost else None, None, None, False)
        return [data.Transaction(meta, datetime.date(2026, 2, 1), "*", None, "sell", frozenset(), frozenset(), [
            data.Posting("Assets:Broker:HOOL", amount.Amount(Decimal("-4"), "HOOL"), lot,
                         amount.Amount(Decimal("160"), "USD"), None, None),
            data.Posting("Assets:Broker:Cash", amount.Amount(Decimal("640"), "USD"), None, None, None, None),
            data.Posting("Income:Gains", None, None, None, None, None)])]


CONFIG = [Broker()]
"""


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "imp.py").write_text(IMPORTER)
    (tmp_path / "s.txt").write_text("statement\n")
    return tmp_path


def _import(books: Path, *flags: str, fitid: str = "", cost: str = "") -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
        TEST_FITID=fitid,
        TEST_COST=cost,
    )
    return subprocess.run(
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


def _rows(result: subprocess.CompletedProcess[str]) -> list[dict[str, Any]]:
    payload = json.loads(result.stdout or result.stderr)
    data = payload["data"] if "data" in payload else payload["error"]["result"]
    return list(data["rows"])


def test_a_hand_entered_twin_is_a_possible_duplicate(books: Path) -> None:
    (books / "main.bean").write_text(LEDGER + SALE.format(meta=""))
    before = (books / "main.bean").read_bytes()

    result = _import(books, "--apply")

    assert result.returncode == 4, result.stderr
    assert [row["status"] for row in _rows(result)] == ["possible_duplicate"]
    assert (books / "main.bean").read_bytes() == before


def test_a_reimport_under_a_native_id_is_an_exact_duplicate(books: Path) -> None:
    (books / "main.bean").write_text(LEDGER)
    first = _import(books, "--apply", fitid="SELL1")
    assert first.returncode == 0, first.stderr
    written = (books / "main.bean").read_bytes()

    again = _import(books, "--apply", fitid="SELL1")

    assert again.returncode == 0, again.stderr
    assert [row["status"] for row in _rows(again)] == ["duplicate"]
    assert (books / "main.bean").read_bytes() == written


def test_an_id_written_before_lots_were_hashed_still_matches(books: Path) -> None:
    (books / "main.bean").write_text(LEDGER + SALE.format(meta=LEGACY_ID))

    result = _import(books)

    assert result.returncode == 0, result.stderr
    assert [row["status"] for row in _rows(result)] == ["duplicate"]


def test_a_stated_lot_booking_did_not_choose_is_still_a_conflict(books: Path) -> None:
    (books / "main.bean").write_text(LEDGER)
    assert _import(books, "--apply", fitid="SELL1").returncode == 0

    result = _import(books, "--apply", fitid="SELL1", cost="170")

    assert result.returncode == 4, result.stderr
    assert [row["status"] for row in _rows(result)] == ["conflict"]
