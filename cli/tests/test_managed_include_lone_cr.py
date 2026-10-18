"""A lone CR above a rewritten managed include leaves the user's own lines alone (w5/475).

The rewrite counted lines with `splitlines`, which also breaks on a lone `\\r`;
the lexer counts `\\n` only. A CR pasted into a comment moved the swap of a
repeated feed include onto the line before it: the user's price was commented
out of the load and of `price export`, and `check` failed on the include.
"""

from __future__ import annotations

from pathlib import Path

from tests.test_price import _run_bea
from tests.test_price import feed_server as feed_server


def _books(tmp_path: Path, feed_server: str) -> Path:
    include = f'include "{feed_server}/prices/BTC-USD"\n'
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text(
        'option "operating_currency" "USD"\n'
        + include
        + "2026-01-01 open Assets:Crypto BTC\n2026-01-01 open Assets:Cash USD\n"
        + '2026-01-02 * "Buy BTC"\n  Assets:Crypto  1 BTC {50000 USD}\n  Assets:Cash  -50000 USD\n'
        + 'include "sub.bean"\n'
    )
    (books / "sub.bean").write_bytes(
        b"; memo pasted from bank\r export\n2026-10-16 price BTC 70000 USD\n" + include.encode()
    )
    return books / "main.bean"


def test_the_load_keeps_the_price_above_the_repeated_include(feed_server: str, tmp_path: Path) -> None:
    ledger = _books(tmp_path, feed_server)

    checked = _run_bea(tmp_path, feed_server, "--file", str(ledger), "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr

    prices = _run_bea(tmp_path, feed_server, "--file", str(ledger), "list", "price")
    assert prices.returncode == 0, prices.stderr
    assert "70000 USD" in prices.stdout
    assert "112000.00 USD" in prices.stdout


def test_the_export_replaces_the_include_and_keeps_the_price(feed_server: str, tmp_path: Path) -> None:
    ledger = _books(tmp_path, feed_server)
    out = tmp_path / "out"

    exported = _run_bea(tmp_path, feed_server, "--file", str(ledger), "price", "export", "--output", str(out))

    assert exported.returncode == 0, exported.stderr
    lines = (out / "sub.bean").read_bytes().split(b"\n")
    assert lines[0] == b"; memo pasted from bank\r export"
    assert lines[1] == b"2026-10-16 price BTC 70000 USD"
    assert lines[2].startswith(b"; managed price feed already included")
    assert b"include" not in lines[2].split(b";", 1)[0]
    checked = _run_bea(tmp_path, feed_server, "--file", str(out / "main.bean"), "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr
