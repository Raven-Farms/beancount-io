"""Two same-day trades of one share count at different costs are two rows (w5/349).

The generated import-id and the possible-duplicate fingerprint hashed the
source posting's units only, so a second buy of `10 AAPL` at another price
was skipped as an exact duplicate of the first, with exit 0.
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
2026-01-01 open Assets:Cash USD
2026-01-01 open Assets:Broker
2026-01-01 open Equity:Opening
2026-01-02 * "Seed"
  Assets:Cash  10000 USD
  Equity:Opening
"""
# What the release before this fix wrote for the 100 USD buy: a units-only id.
LEGACY_A = """2026-01-05 * "Broker" "Buy AAPL"
  import-id: "csv:sha256:fd25259e21688a59"
  Assets:Broker  10 AAPL {100 USD}
  Assets:Cash  -1000 USD
"""
IMPORTER = """\
import datetime
from decimal import Decimal as D
from beancount.core import amount, data, position


class Trades:
    name = "trades"

    def identify(self, filepath):
        return filepath.endswith(".txt")

    def account(self, filepath):
        return "Assets:Broker"

    def extract(self, filepath, existing):
        out = []
        for line in open(filepath).read().split("\\n"):
            if not line.strip():
                continue
            cost, cash = line.split()
            lot = position.CostSpec(D(cost), None, "USD", None, None, False)
            postings = [
                data.Posting("Assets:Broker", amount.Amount(D("10"), "AAPL"), lot, None, None, None),
                data.Posting("Assets:Cash", amount.Amount(D(cash), "USD"), None, None, None, None),
            ]
            meta = data.new_metadata("x", 1)
            day = datetime.date(2026, 1, 5)
            out.append(data.Transaction(meta, day, "*", "Broker", "Buy AAPL", frozenset(), frozenset(), postings))
        return out


CONFIG = [Trades()]
"""


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "imp.py").write_text(IMPORTER)
    (tmp_path / "a.txt").write_text("100 -1000\n")
    (tmp_path / "b.txt").write_text("120 -1200\n")
    (tmp_path / "both.txt").write_text("100 -1000\n120 -1200\n")
    return tmp_path


def _import(books: Path, export: str, *flags: str) -> Any:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "--json",
            "--no-input",
            "-f",
            "main.bean",
            "import",
            export,
            "--config",
            "imp.py",
            *flags,
        ],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["data"]


def _statuses(data: Any) -> list[str]:
    return [row["status"] for row in data["rows"]]


def test_a_later_trade_at_another_cost_is_new(books: Path) -> None:
    (books / "main.bean").write_text(LEDGER)
    _import(books, "a.txt", "--apply")
    assert _statuses(_import(books, "b.txt")) == ["new"]
    assert _import(books, "b.txt", "--apply")["written"] == 1
    text = (books / "main.bean").read_text()
    assert "{100 USD}" in text and "{120 USD}" in text
    assert _statuses(_import(books, "b.txt")) == ["duplicate"]


def test_one_export_holding_both_trades_writes_both(books: Path) -> None:
    (books / "main.bean").write_text(LEDGER)
    assert _statuses(_import(books, "both.txt")) == ["new", "new"]


def test_an_id_written_before_the_fix_still_matches_its_own_lot(books: Path) -> None:
    (books / "main.bean").write_text(LEDGER + LEGACY_A)
    assert _statuses(_import(books, "a.txt")) == ["duplicate"]
    assert _statuses(_import(books, "b.txt")) == ["new"]
