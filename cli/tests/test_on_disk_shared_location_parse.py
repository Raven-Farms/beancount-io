"""`list --on-disk` reads the entry a shared location spells with the parser (w5/507).

Two entries at one location were told apart by the first two quoted strings
on the header line: a quoted word in a `;` comment was taken for the
narration, and a narration spanning lines never matched, so the real
transaction counted as generated. Only transactions were checked, so a
plugin's inverse `price` at a price line passed as on disk.
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
PLUGIN = """from decimal import Decimal
from beancount.core import data
__plugins__ = ["run"]
def run(entries, options_map, config=None):
    out = []
    for e in entries:
        out.append(e)
        if isinstance(e, data.Transaction) and "inv" in e.tags:
            meta = data.new_metadata(e.meta["filename"], e.meta["lineno"])
            out.append(data.Transaction(meta, e.date, "*", "Broker", "fee (generated)", frozenset({"gen"}),
                frozenset(), [
                    data.Posting("Expenses:Fees", data.Amount(Decimal("1"), "USD"), None, None, None, None),
                    data.Posting("Assets:Cash", data.Amount(Decimal("-1"), "USD"), None, None, None, None)]))
        if isinstance(e, data.Price) and e.currency == "HOOL":
            meta = data.new_metadata(e.meta["filename"], e.meta["lineno"])
            out.append(data.Price(meta, e.date, "USD", data.Amount(Decimal(1) / e.amount.number, "HOOL")))
    return out, []
"""
LEDGER = """option "insert_pythonpath" "TRUE"
plugin "myplug"
option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Fees USD
2026-01-01 open Equity:Opening USD
2026-01-01 commodity HOOL
2026-01-02 * "seed"
  Assets:Cash 1000 USD
  Equity:Opening
2026-01-05 * "buy" #inv ; see "receipt" folder
  Expenses:Fees 10 USD
  Assets:Cash
2026-01-06 * "Shop" "multi
line" #inv
  Expenses:Fees 10 USD
  Assets:Cash
2026-01-07 price HOOL 50 USD
"""


def _list(tmp_path: Path, kind: str, *flags: str) -> list[dict[str, Any]]:
    (tmp_path / "myplug.py").write_text(PLUGIN)
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), "list", kind, *flags],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return list(json.loads(result.stdout)["data"])


def test_on_disk_keeps_the_written_transactions_and_drops_the_fees(tmp_path: Path) -> None:
    rows = _list(tmp_path, "transaction", "--on-disk")

    assert sorted(row["narration"] for row in rows) == ["buy", "multi\nline", "seed"]


def test_the_full_listing_labels_only_the_fees_generated(tmp_path: Path) -> None:
    rows = _list(tmp_path, "transaction")

    generated = sorted(row["narration"] for row in rows if row.get("generated"))
    assert generated == ["fee (generated)", "fee (generated)"]


@pytest.mark.parametrize("flags", [("--on-disk",)])
def test_a_plugin_price_at_a_price_line_is_not_on_disk(tmp_path: Path, flags: tuple[str, ...]) -> None:
    rows = _list(tmp_path, "price", *flags)

    assert [(row["currency"], row["amount"]["currency"]) for row in rows] == [("HOOL", "USD")]
