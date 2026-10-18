"""A same-day price in each direction values a holding one way everywhere (w5/556).

Fava's price map appended each rate and its inverse in entry order and kept
the last of the day, while Beancount's settles the pair first (the inverse of
the direction quoted less often wins). `balance` and `report` then valued EUR
at 1.20 and `bea query` at 1.25, and moving one line flipped `balance`.
`add price` also wrote the disagreeing reciprocal quote without a conflict.
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
plugin "beancount.plugins.implicit_prices"

2026-01-01 open Assets:EUR EUR
2026-01-01 open Assets:USD USD
2026-01-01 open Equity:Opening

2026-01-01 price EUR 1.10 USD

2026-01-02 * "Open"
  Assets:EUR  1000.00 EUR
  Equity:Opening
"""
BUY = '2026-01-05 * "Buy USD with EUR"\n  Assets:USD  100.00 USD @ 0.80 EUR\n  Assets:EUR  -80.00 EUR\n'
QUOTE = "2026-01-05 price EUR 1.20 USD\n"
ORDERS = {"quote-last": HEADER + "\n" + BUY + "\n" + QUOTE, "quote-first": HEADER + "\n" + QUOTE + "\n" + BUY}


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _data(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["data"]


@pytest.mark.parametrize("order", ORDERS.values(), ids=ORDERS.keys())
def test_balance_report_and_query_agree_in_either_line_order(tmp_path: Path, order: str) -> None:
    (tmp_path / "main.bean").write_text(order, encoding="utf-8")

    balance = _data(_bea(tmp_path, "balance", "Assets:EUR"))
    sheet = _data(_bea(tmp_path, "report", "balance-sheet"))
    query = _data(_bea(tmp_path, "query", "SELECT convert(sum(position), 'USD') AS v WHERE account = 'Assets:EUR'"))

    # 920 EUR at 1.25, the inverse of the implicit `USD 0.80 EUR`, as Beancount settles it.
    assert "1150.00" in json.dumps(balance), balance
    assert sheet["net_worth"] == {"USD": "1250.0000"}, sheet["net_worth"]
    assert json.dumps(query["rows"]).count("1150.0000") == 1, query["rows"]


def test_add_price_refuses_a_disagreeing_reciprocal_quote(tmp_path: Path) -> None:
    ledger = 'option "operating_currency" "USD"\n2026-01-01 commodity EUR\n2026-01-05 price USD 0.80 EUR\n'
    (tmp_path / "main.bean").write_text(ledger, encoding="utf-8")
    quote = ["add", "price", "--date", "2026-01-05", "--currency", "EUR"]

    refused = _bea(tmp_path, *quote, "--amount", "1.20 USD")

    assert refused.returncode == 4, refused.stdout
    error = json.loads(refused.stderr)["error"]["message"]
    assert error.startswith("USD already has a 2026-01-05 price of 0.80 EUR (at "), error
    assert "the other direction of this pair, and 1.20 USD disagrees with it. Pass --force" in error
    assert (tmp_path / "main.bean").read_text(encoding="utf-8") == ledger
    # The same rate the other way round agrees, and --force records a disagreeing one.
    assert _bea(tmp_path, *quote, "--amount", "1.25 USD").returncode == 0
    assert _bea(tmp_path, *quote, "--amount", "1.30 USD", "--force").returncode == 0
    assert (tmp_path / "main.bean").read_text(encoding="utf-8").count("price EUR") == 2
