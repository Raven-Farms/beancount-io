"""Shadowing a feed point comments out every indented line under it (w5/477).

The walk stopped at the first line that was not `key: value`, so an indented
comment between a point's metadata lines ended it and left the metadata
below indented under nothing: `unexpected INDENT` in every command, and
`bea add price` refused a valid quote.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bea_engine.managed_load import apply_ledger_price_precedence
from tests.test_price import _FeedHandler, _run_bea
from tests.test_price import feed_server as feed_server

FEED = """\
; alias: K2
; commodity: XC
; quote: USD
2026-10-15 price XC 10 USD
    ; provider note
  observed-at: "2026-10-16T12:00:00Z"

2026-10-16 price XC 11 USD
  observed-at: "2026-10-16T12:00:00Z"
"""


def test_every_indented_line_of_the_point_is_commented() -> None:
    point = SimpleNamespace(date="2026-10-15", base="XC", quote="USD", line=4)
    kept = SimpleNamespace(date="2026-10-16", base="XC", quote="USD", line=8)

    effective = apply_ledger_price_precedence(FEED, (point, kept), {("2026-10-15", "XC", "USD")})

    lines = effective.text.split("\n")
    assert len(lines) == len(FEED.split("\n"))
    assert lines[3].startswith("; shadowed")
    assert lines[4:7] == ["; ; provider note", '; observed-at: "2026-10-16T12:00:00Z"', ""]
    assert lines[7:9] == FEED.split("\n")[7:9]
    assert effective.effective_dates == ("2026-10-16",)


def test_add_price_shadows_the_point(feed_server: str, tmp_path: Path) -> None:
    _FeedHandler.routes["/prices/K2"] = {
        "body": FEED.encode(),
        "headers": {"Content-Type": "text/plain; charset=utf-8", "ETag": '"k2"'},
        "etag": '"k2"',
        "etag_match": True,
    }
    ledger = tmp_path / "main.bean"
    ledger.write_text(f'include "{feed_server}/prices/K2"\n2026-01-01 open Assets:Cash USD\n')
    assert _run_bea(tmp_path, feed_server, "--file", str(ledger), "check").returncode == 0

    added = _run_bea(
        tmp_path,
        feed_server,
        "--file",
        str(ledger),
        "add",
        "price",
        "--date",
        "2026-10-15",
        "-c",
        "XC",
        "--amount",
        "12 USD",
    )

    assert added.returncode == 0, added.stdout + added.stderr
    assert "2026-10-15 price XC" in ledger.read_text()
    checked = _run_bea(tmp_path, feed_server, "--file", str(ledger), "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr
