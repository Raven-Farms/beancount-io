"""A price the ledger declares wins after a byte-order mark or below an ignored line with a `"` (w5/476).

The text scan that finds authored prices missed both: the mark hid a price on
line 1, and a `"` on a line Beancount ignores (an org-mode heading) opened a
string that masked the price below it. The feed's point stayed in force.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bea_engine.managed_load import collect_ledger_price_pairs
from tests.test_price import _run_bea
from tests.test_price import feed_server as feed_server

PAIR = ("2026-09-10", "BTC", "USD")
# A later string: the stray `"` above the price pairs with its opening quote.
LATER = '2026-09-12 * "Later"\n'


@pytest.mark.parametrize(
    "text",
    [
        "﻿2026-09-10 price BTC 70000 USD\n",
        '* Prices for the 12" binder\n2026-09-10 price BTC 70000 USD\n' + LATER,
        '# a 27" monitor\n2026-09-10 price BTC 70000 USD\n' + LATER,
        '! flagged "note\n2026-09-10 price BTC 70000 USD\n' + LATER,
    ],
    ids=["byte-order-mark", "org-heading", "hash-line", "flag-line"],
)
def test_the_scan_finds_the_authored_price(text: str) -> None:
    assert PAIR in collect_ledger_price_pairs(text)


def test_a_price_inside_a_string_is_still_not_one() -> None:
    text = '2026-01-01 note Assets:Cash "first\n2026-09-10 price BTC 70000 USD\n"\n'
    assert PAIR not in collect_ledger_price_pairs(text)


@pytest.mark.parametrize("layout", ["bom-include", "org-heading"])
def test_the_authored_price_shadows_the_feed(feed_server: str, tmp_path: Path, layout: str) -> None:
    ledger = tmp_path / "main.bean"
    head = f'option "operating_currency" "USD"\ninclude "{feed_server}/prices/BTC-USD"\n'
    tail = (
        "2026-01-01 open Assets:Crypto BTC\n2026-01-01 open Assets:Cash USD\n"
        '2026-01-02 * "Buy BTC"\n  Assets:Crypto  1 BTC {50000 USD}\n  Assets:Cash  -50000 USD\n'
    )
    if layout == "bom-include":
        (tmp_path / "prices.bean").write_bytes(b"\xef\xbb\xbf2026-09-10 price BTC 70000 USD\n")
        ledger.write_text(head + tail + 'include "prices.bean"\n')
    else:
        # As the note placed it: after the include, above the buy's `"Buy BTC"`.
        ledger.write_text(head + '* Prices for the 12" binder\n2026-09-10 price BTC 70000 USD\n' + tail)

    status = _run_bea(tmp_path, feed_server, "--json", "--file", str(ledger), "price", "status")
    assert status.returncode == 0, status.stderr
    assert [source["shadowed_count"] for source in json.loads(status.stdout)["data"]["sources"]] == [1]

    # The feed's 112000 point for the same day gives way to the authored one.
    priced = _run_bea(
        tmp_path, feed_server, "--file", str(ledger), "query", "SELECT getprice('BTC', 'USD', 2026-09-10) AS p LIMIT 1"
    )
    assert priced.returncode == 0, priced.stderr
    assert priced.stdout.split()[-1] == "70000"
