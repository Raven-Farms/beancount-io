"""`price export` of a feed included more than once writes a snapshot that loads (w5/100).

Loading keeps a feed's first include and ignores repeats. The export rewrote
every occurrence to the same local feed file, and Beancount refuses a file
included twice, so the "self-contained copy for stock tools" did not load.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_price import _run_bea
from tests.test_price import feed_server as feed_server

CHILD = """\
{include}2026-01-02 * "Open"
  Assets:Wallet  2 BTC {{50000 USD}}
  Equity:Opening
"""


def _books(tmp_path: Path, feed_server: str, *, root: int, child: int) -> Path:
    line = f'include "{feed_server}/prices/BTC-USD"\n'
    books = tmp_path / "books"
    (books / "y").mkdir(parents=True)
    (books / "main.bean").write_text(
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Wallet BTC\n2026-01-01 open Equity:Opening\n'
        + line * root
        + 'include "y/2026.bean"\n'
    )
    (books / "y" / "2026.bean").write_text(CHILD.format(include=line * child))
    return books / "main.bean"


def _stock_check(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "beancount.scripts.check", str(target)], capture_output=True, text=True, timeout=60
    )


@pytest.mark.parametrize(
    ("root", "child"), [(1, 1), (2, 0), (2, 1), (0, 2)], ids=["root+child", "root-twice", "all-three", "child-twice"]
)
def test_a_repeated_feed_include_exports_to_a_snapshot_that_loads(
    feed_server: str, tmp_path: Path, root: int, child: int
) -> None:
    ledger = _books(tmp_path, feed_server, root=root, child=child)
    out = tmp_path / "out"
    assert _run_bea(tmp_path, feed_server, "--file", str(ledger), "check").returncode == 0

    exported = _run_bea(tmp_path, feed_server, "--file", str(ledger), "price", "export", "--output", str(out))

    assert exported.returncode == 0, exported.stderr
    assert "Exported 3 files" in exported.stdout
    checked = _run_bea(tmp_path, feed_server, "--file", str(out / "main.bean"), "check")
    assert checked.returncode == 0, checked.stderr + checked.stdout
    assert _stock_check(out / "main.bean").returncode == 0
    copies = (out / "main.bean").read_text() + (out / "y" / "2026.bean").read_text()
    assert copies.count("BTC-USD.beancount") == 1
    assert copies.count("; managed price feed already included") == root + child - 1
    prices = _run_bea(tmp_path, feed_server, "--file", str(out / "main.bean"), "list", "price")
    assert prices.stdout.count("112000.00 USD") == 1
    # Every other line stays where it was.
    for name in ("main.bean", "y/2026.bean"):
        before = (ledger.parent / name).read_text().split("\n")
        after = (out / name).read_text().split("\n")
        assert len(after) == len(before)
        assert [line for line in after if "include" not in line] == [line for line in before if "include" not in line]


def test_a_single_include_exports_as_before(feed_server: str, tmp_path: Path) -> None:
    ledger = _books(tmp_path, feed_server, root=1, child=0)
    out = tmp_path / "out"

    exported = _run_bea(tmp_path, feed_server, "--file", str(ledger), "price", "export", "--output", str(out))

    assert exported.returncode == 0, exported.stderr
    text = (out / "main.bean").read_text()
    assert 'include "prices/BTC-USD.beancount"' in text and "already included" not in text
    assert (out / "y" / "2026.bean").read_text() == (ledger.parent / "y" / "2026.bean").read_text()
    assert _stock_check(out / "main.bean").returncode == 0
